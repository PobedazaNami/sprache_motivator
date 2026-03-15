"""Quick test: can we fetch subtitles with cookies?"""
import requests
from http.cookiejar import MozillaCookieJar
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import RequestBlocked, TranscriptsDisabled

COOKIE_PATH = "/app/cookies/youtube_cookies.txt"
VIDEO_ID = "iFOUdu-aKzM"

jar = MozillaCookieJar(COOKIE_PATH)
jar.load(ignore_discard=True, ignore_expires=True)
print(f"Loaded {len(jar)} cookies")

session = requests.Session()
session.cookies = jar

try:
    api = YouTubeTranscriptApi(http_client=session)
    transcript_list = api.list(VIDEO_ID)
    langs = [t.language_code for t in transcript_list]
    print(f"Available languages: {langs}")
    transcript = transcript_list.find_transcript(["de", "de-DE", "en"])
    data = transcript.fetch().to_raw_data()
    print(f"Got {len(data)} cues, first: {data[0] if data else 'none'}")
except RequestBlocked as e:
    print(f"BLOCKED: {e}")
except TranscriptsDisabled as e:
    print(f"DISABLED: {e}")
except Exception as e:
    print(f"ERROR ({type(e).__name__}): {e}")
