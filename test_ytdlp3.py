"""Test: yt-dlp subtitle extraction via Python API."""
import json
import shutil
import yt_dlp
import os

VIDEO_ID = "iFOUdu-aKzM"
COOKIE_SRC = "/app/cookies/youtube_cookies.txt"
COOKIE_TMP = "/tmp/yt_cookies.txt"
shutil.copy2(COOKIE_SRC, COOKIE_TMP)

ydl_opts = {
    "cookiefile": COOKIE_TMP,
    "skip_download": True,
    "writesubtitles": True,
    "writeautomaticsub": True,
    "subtitleslangs": ["de", "en"],
    "subtitlesformat": "json3",
    "quiet": True,
    "no_warnings": True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(f"https://www.youtube.com/watch?v={VIDEO_ID}", download=False)

print("Title:", info.get("title"))
print("Duration:", info.get("duration"))

subs = info.get("subtitles", {})
auto_subs = info.get("automatic_captions", {})

print(f"\nManual subtitles: {list(subs.keys())}")
print(f"Auto captions: {list(auto_subs.keys())[:10]}")

# Try to get German subtitles
for lang in ["de", "en"]:
    sub_list = subs.get(lang, []) or auto_subs.get(lang, [])
    if sub_list:
        # Find json3 format
        json3 = [s for s in sub_list if s.get("ext") == "json3"]
        if json3:
            url = json3[0]["url"]
            print(f"\n{lang} json3 URL found ({len(url)} chars)")
            # Download it
            import requests
            sess = requests.Session()
            resp = sess.get(url, timeout=15)
            print(f"Response: {resp.status_code}, {len(resp.text)} bytes")
            data = resp.json()
            events = data.get("events", [])
            print(f"Events: {len(events)}")
            if events:
                # Show first few with text
                shown = 0
                for e in events:
                    segs = e.get("segs", [])
                    text = "".join(s.get("utf8", "") for s in segs).strip()
                    if text and text != "\n":
                        print(f"  [{e.get('tStartMs', 0)}ms] {text}")
                        shown += 1
                        if shown >= 3:
                            break
            break
