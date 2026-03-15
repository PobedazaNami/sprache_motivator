"""Test: requests with cookies from cookie file for subtitle download."""
import yt_dlp
import shutil
import os
import json
import traceback
import http.cookiejar

VIDEO_ID = 'iFOUdu-aKzM'

try:
    src = '/app/cookies/youtube_cookies.txt'
    dst = '/tmp/yt_cookies.txt'
    shutil.copy2(src, dst)
    print('Cookie copy OK, size:', os.path.getsize(dst))

    # Get subtitle URL via extract_info
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['de'],
        'subtitlesformat': 'json3',
        'quiet': True,
        'no_warnings': True,
        'ignore_no_formats_error': True,
        'cookiefile': dst,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f'https://www.youtube.com/watch?v={VIDEO_ID}', download=False)
        auto = info.get('automatic_captions', {})
        de_list = auto.get('de', [])
        json3_entries = [s for s in de_list if s.get('ext') == 'json3']
        if not json3_entries:
            print('No json3!')
            exit()
        url = json3_entries[0]['url']
        print(f'Got URL (len={len(url)})')

    # Load cookies from Netscape cookie file
    import requests
    cj = http.cookiejar.MozillaCookieJar(dst)
    cj.load(ignore_discard=True, ignore_expires=True)
    print(f'Loaded {len(cj)} cookies')

    session = requests.Session()
    session.cookies = cj
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
        'Referer': f'https://www.youtube.com/watch?v={VIDEO_ID}',
    })

    print('\n=== Test: requests with browser cookies ===')
    resp = session.get(url, timeout=15)
    print(f'Status: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        events = data.get('events', [])
        print(f'SUCCESS! Events: {len(events)}')
        if len(events) > 1:
            segs = events[1].get('segs', [])
            print(f'  Event[1] segs={len(segs)}, has tOffsetMs: {any("tOffsetMs" in s for s in segs)}')
    else:
        print(f'Body: {resp.text[:300]}')

except Exception:
    traceback.print_exc()
