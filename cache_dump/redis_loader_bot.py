"""Load subtitles JSON into Redis (run inside bot container)."""
import asyncio
import json
import sys
sys.path.insert(0, "/app")

async def main():
    from bot.services.redis_service import redis_service
    await redis_service.connect()
    
    with open("/tmp/subtitles.json", "r") as f:
        data = json.load(f)
    
    ttl = 604800  # 7 days
    for vid, value in data.items():
        key = f"subtitle:session:{vid}"
        await redis_service.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
        print(f"OK: {vid} ({len(value.get('cues', []))} cues)")
    
    print(f"\nDone! Loaded {len(data)} videos into Redis.")

asyncio.run(main())
