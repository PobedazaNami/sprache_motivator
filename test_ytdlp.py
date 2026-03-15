"""Test: yt-dlp urlopen with cookies for subtitle download."""
import yt_dlp
import shutil
import os
import json
import traceback

VIDEO_ID = 'iFOUdu-aKzM'
LANGS = ['de', 'de-DE', 'en']

try:
    src = '/app/cookies/youtube_cookies.txt'
    dst = '/tmp/yt_cookies.txt'
    shutil.copy2(src, dst)
    print('Cookie copy OK, size:', os.path.getsize(dst))

    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': LANGS,
        'subtitlesformat': 'json3',
        'quiet': True,
        'no_warnings': True,
        'ignore_no_formats_error': True,
        'cookiefile': dst,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f'https://www.youtube.com/watch?v={VIDEO_ID}', download=False)
        subs = info.get('subtitles', {})
        auto = info.get('automatic_captions', {})
        print('Subs langs:', list(subs.keys())[:5])
        print('Auto langs:', list(auto.keys())[:5])

        for lang in LANGS:
            sub_list = subs.get(lang, []) or auto.get(lang, [])
            json3_entries = [s for s in sub_list if s.get('ext') == 'json3']
            if not json3_entries:
                continue
            url = json3_entries[0]['url']
            print(f'\nTrying {lang} via ydl.urlopen()...')
            try:
                resp = ydl.urlopen(url)
                raw = resp.read().decode('utf-8')
                data = json.loads(raw)
                events = data.get('events', [])
                print(f'SUCCESS! Events: {len(events)}, size: {len(raw)} bytes')
                if len(events) > 1:
                    print('Event[1]:', json.dumps(events[1], ensure_ascii=False)[:200])
                break
            except Exception as e:
                print(f'FAILED: {e}')
except Exception:
    traceback.print_exc()
