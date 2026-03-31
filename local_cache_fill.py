"""
Local script: fetch subtitles from YouTube (from non-blocked IP)
and upload directly to Redis on server via SSH tunnel.

Run: python local_cache_fill.py
"""
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import requests
import yt_dlp

CHANNEL_FEED = "https://www.youtube.com/feeds/videos.xml?user=KurzgesagtDE"
LANG_PRIORITY = ["de", "de-DE"]
REDIS_TTL = 604800  # 7 days
SERVER = "root@49.13.219.223"
LIMIT = 15
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "cache_dump")


def get_channel_videos(limit=15):
    resp = requests.get(CHANNEL_FEED, timeout=15)
    resp.raise_for_status()
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(resp.text)
    items = []
    for entry in root.findall("atom:entry", ns)[:limit]:
        vid = entry.findtext("yt:videoId", namespaces=ns)
        title = entry.findtext("atom:title", default="", namespaces=ns)
        if vid and title:
            items.append({"videoId": vid, "title": title})
    return items


def fetch_subtitles(video_id):
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": LANG_PRIORITY,
        "subtitlesformat": "json3",
        "quiet": True,
        "no_warnings": True,
        "ignore_no_formats_error": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}", download=False
        )

    subs = info.get("subtitles", {})
    auto_subs = info.get("automatic_captions", {})
    all_langs = list(dict.fromkeys(list(subs.keys()) + list(auto_subs.keys())))

    for lang in LANG_PRIORITY:
        sub_list = subs.get(lang, []) or auto_subs.get(lang, [])
        if not sub_list:
            continue
        json3_entries = [s for s in sub_list if s.get("ext") == "json3"]
        if not json3_entries:
            continue
        url = json3_entries[0]["url"]
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            continue
        data = resp.json()
        events = data.get("events", [])
        cues = cues_from_json3(events)
        if cues:
            return cues, lang, all_langs

    return [], "", all_langs


def cues_from_json3(events):
    cues = []
    for event in events:
        segs = event.get("segs", [])
        text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if not text:
            continue
        start_ms = event.get("tStartMs", 0)
        dur_ms = event.get("dDurationMs", 2000)
        cues.append({"startMs": start_ms, "endMs": start_ms + dur_ms, "text": text})
    return cues


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Fetching channel videos...")
    videos = get_channel_videos(LIMIT)
    print(f"Found {len(videos)} videos")

    results = {}
    for i, video in enumerate(videos):
        vid = video["videoId"]
        title = video["title"]
        print(f"\n[{i+1}/{len(videos)}] {vid}: {title[:50]}...")
        try:
            cues, lang, all_langs = fetch_subtitles(vid)
            if not cues:
                print(f"  -> No DE subtitles found")
                continue
            result = {
                "videoId": vid,
                "title": title,
                "cues": cues,
                "selectedLanguage": lang,
                "availableLanguages": all_langs,
            }
            results[vid] = result
            print(f"  -> OK: {len(cues)} cues, lang={lang}")
        except Exception as e:
            print(f"  -> ERROR: {e}")
        time.sleep(2)  # gentle delay

    # Save to file
    dump_path = os.path.join(OUTPUT_DIR, "subtitles.json")
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"\nSaved {len(results)} videos to {dump_path}")

    # Generate redis-cli commands
    redis_script = os.path.join(OUTPUT_DIR, "load_redis.sh")
    with open(redis_script, "w", encoding="utf-8", newline="\n") as f:
        f.write("#!/bin/bash\n")
        f.write("# Load subtitles into Redis\n")
        for vid, data in results.items():
            json_str = json.dumps(data, ensure_ascii=False)
            # Escape for shell
            escaped = json_str.replace("\\", "\\\\").replace("'", "'\\''")
            f.write(f"redis-cli SET 'subtitle:session:{vid}' '{escaped}' EX {REDIS_TTL}\n")
    print(f"Redis load script: {redis_script}")

    # Upload to server and execute
    print(f"\nUploading to server...")
    scp_result = subprocess.run(
        ["scp", dump_path, f"{SERVER}:/tmp/subtitles.json"],
        capture_output=True, text=True
    )
    if scp_result.returncode != 0:
        print(f"SCP failed: {scp_result.stderr}")
        return

    # Upload a Python loader script
    loader = os.path.join(OUTPUT_DIR, "redis_loader.py")
    with open(loader, "w", encoding="utf-8") as f:
        f.write("""
import json
import subprocess

with open("/tmp/subtitles.json", "r") as fh:
    data = json.load(fh)

for vid, value in data.items():
    json_str = json.dumps(value, ensure_ascii=False)
    cmd = ["redis-cli", "-p", "6379", "SET", f"subtitle:session:{vid}", json_str, "EX", "604800"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"OK: {vid}")
    else:
        print(f"FAIL: {vid}: {r.stderr}")
print("Done!")
""")

    subprocess.run(["scp", loader, f"{SERVER}:/tmp/redis_loader.py"], check=True)
    print("Loading into Redis...")
    result = subprocess.run(
        ["ssh", SERVER, "cd /opt/sprache_motivator && docker cp /tmp/subtitles.json sprache_motivator-redis-1:/tmp/subtitles.json && docker cp /tmp/redis_loader.py sprache_motivator-redis-1:/tmp/redis_loader.py && docker compose exec -T redis python3 /tmp/redis_loader.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        # Redis container might not have python, use alternative
        print(f"Python approach failed, trying pipe approach...")
        result2 = subprocess.run(
            ["ssh", SERVER, "cd /opt/sprache_motivator && docker cp /tmp/subtitles.json sprache_motivator-bot-1:/tmp/subtitles.json && docker cp /tmp/redis_loader.py sprache_motivator-bot-1:/tmp/redis_loader_remote.py && docker compose exec -T bot python3 /tmp/redis_loader_remote.py"],
            capture_output=True, text=True
        )
        print(result2.stdout)
        if result2.returncode != 0:
            print(f"Error: {result2.stderr}")
    else:
        print(result.stdout)

    print("\nDone! Subtitles loaded into Redis cache.")


if __name__ == "__main__":
    main()
