
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
