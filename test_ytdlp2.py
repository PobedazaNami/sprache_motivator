"""Test: yt-dlp subtitle extraction with cookies (writable copy)."""
import json
import shutil
import subprocess
import sys
import os

VIDEO_ID = "iFOUdu-aKzM"
COOKIE_SRC = "/app/cookies/youtube_cookies.txt"
COOKIE_TMP = "/tmp/yt_cookies.txt"

shutil.copy2(COOKIE_SRC, COOKIE_TMP)

cmd = [
    sys.executable, "-m", "yt_dlp",
    "--cookies", COOKIE_TMP,
    "--write-subs",
    "--write-auto-subs",
    "--sub-lang", "de",
    "--sub-format", "json3",
    "--skip-download",
    "--no-warnings",
    "--ignore-errors",
    "-o", "/tmp/yt_test",
    f"https://www.youtube.com/watch?v={VIDEO_ID}",
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
print("STDOUT:", result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
print("Return code:", result.returncode)

for f in os.listdir("/tmp"):
    if f.startswith("yt_test"):
        fpath = f"/tmp/{f}"
        size = os.path.getsize(fpath)
        print(f"\nFound: {fpath} ({size} bytes)")
        if size > 0 and (f.endswith(".json3") or f.endswith(".de.vtt") or f.endswith(".de.json3")):
            with open(fpath) as fh:
                content = fh.read()
                print(f"Content preview: {content[:500]}")
