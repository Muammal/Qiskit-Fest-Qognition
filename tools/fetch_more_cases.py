"""Cache further open case-study pages into raw/, with a text copy. Never executes content.

Usage: fetch_more_cases.py [sid=url ...]. Pages already cached are not re-downloaded.
A failure is printed; merge_manifest.py keeps the list in access_failures.json.
"""

import html
import re
import sys
import time
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "disaster_data" / "raw"
USER_AGENT = "Mozilla/5.0 (StrandedResearch; public academic data collection)"
PAUSE_SECONDS = 2.0


def to_text(page: str) -> str:
    page = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))


def fetch(sid: str, url: str) -> None:
    path = RAW / f"{sid}.html"
    if path.exists():
        print(sid, "cached", path.stat().st_size)
        return
    time.sleep(PAUSE_SECONDS)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    path.write_bytes(body)
    text = to_text(body.decode("utf-8", "replace"))
    (RAW / f"{sid}.txt").write_text(text, encoding="utf-8")
    (RAW / f"{sid}.url").write_text(url, encoding="utf-8")
    print(sid, "OK", len(body), "text", len(text))


def main() -> None:
    for arg in sys.argv[1:]:
        sid, url = arg.split("=", 1)
        try:
            fetch(sid, url)
        except Exception as error:  # A blocked page is recorded, not fatal.
            print(sid, "FAILED", repr(error)[:120])


if __name__ == "__main__":
    main()
