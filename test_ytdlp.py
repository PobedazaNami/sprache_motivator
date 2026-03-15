"""Test: yt-dlp subtitle extraction with cookies."""
import json
import subprocess
import sys

VIDEO_ID = "iFOUdu-aKzM"
COOKIE_PATH = "/app/cookies/youtube_cookies.txt"

cmd = [
    sys.executable, "-m", "yt_dlp",
    "--cookies", COOKIE_PATH,
    "--write-subs",
    "--write-auto-subs",
    "--sub-lang", "de",
    "--sub-format", "json3",
    "--skip-download",
    "--no-warnings",
    "-o", "/tmp/yt_test",
    f"https://www.youtube.com/watch?v={VIDEO_ID}",
]

print("Running:", " ".join(cmd))
result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)

# Check if file was created
import os
for f in os.listdir("/tmp"):
    if f.startswith("yt_test"):
        fpath = f"/tmp/{f}"
        print(f"\nFound: {fpath} ({os.path.getsize(fpath)} bytes)")
        if f.endswith(".json3"):
            with open(fpath) as fh:
                data = json.load(fh)
                events = data.get("events", [])
                print(f"Events: {len(events)}")
                if events:
                    print(f"First event: {events[0]}")
