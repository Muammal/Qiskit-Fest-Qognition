"""Check every case-study quote against the cached page text, offline.

Two levels: 'exact' is verbatim after collapsing whitespace, 'normalised' also ignores case,
punctuation and citation markers. Anything else is reported as missing. This never edits data.
"""
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'disaster_data'
RAW = ROOT / 'raw'
MIN_WORDS, MAX_WORDS = 6, 60
BOT_CHALLENGE_BYTES = 1000


def page_text(page: str) -> str:
    page = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', page)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'(?s)<[^>]+>', ' ', page)))


def normalise(text: str) -> str:
    text = re.sub(r'\[\s*\d+\s*\]', ' ', text.lower())
    return re.sub(r'[^a-z0-9]+', '', text)


def source_pages() -> dict[str, str]:
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    pages = {}
    for source in manifest['sources']:
        path = ROOT / source['file']
        if path.suffix == '.html' and path.exists() and path.stat().st_size > BOT_CHALLENGE_BYTES:
            pages[source['url']] = page_text(path.read_text(encoding='utf-8', errors='replace'))
    return pages


def main() -> int:
    cases = json.loads((ROOT / 'case_studies.json').read_text(encoding='utf-8'))['cases']
    pages = source_pages()
    tally, problems = Counter(), []
    for case in cases:
        wikipedia = sum('wikipedia.org' in f['source_url'] for f in case['facts'])
        if wikipedia > len(case['facts']) / 2:
            problems.append((case['id'], 'more than half Wikipedia', wikipedia, len(case['facts'])))
        for fact in case['facts']:
            quote, url = fact['quote'], fact['source_url']
            words = len(quote.split())
            if not MIN_WORDS <= words <= MAX_WORDS or not re.search(r'\d', quote):
                problems.append((case['id'], fact['key'], 'quote shape', words))
            if 'wikipedia.org' in url and fact['source_type'] == 'primary':
                problems.append((case['id'], fact['key'], 'Wikipedia marked primary'))
            text = pages.get(url)
            if text is None:
                tally['no_page'] += 1
                problems.append((case['id'], fact['key'], 'no cached page', url))
            elif re.sub(r'\s+', ' ', quote) in text:
                tally['exact'] += 1
            elif normalise(quote) in normalise(text):
                tally['normalised'] += 1
                print('normalised only:', case['id'], fact['key'], quote[:70])
            else:
                tally['missing'] += 1
                problems.append((case['id'], fact['key'], 'quote not found', quote[:80]))
    print(dict(tally))
    for problem in problems:
        print('PROBLEM', problem)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
