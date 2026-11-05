"""Parse Einarsson (2018) Table 1 from the cached page into disaster_data/precursor_rows.json.

ICELAND ONLY. The table covers Icelandic eruptions 1966-2014 and must not be used as a global
or tropical lead-time distribution.

Rules, taken from the table's own legend:
- "~" means the timing is imprecise and "( )" means the beginning of the eruption is assumed.
  Both give a stated value, so it is kept, and the original cell stays visible in quote_or_row.
- A range ("2 1/2-15 h") or an empty cell has no single value, so lead_hours stays null.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'disaster_data'
SOURCE_URL = 'https://www.frontiersin.org/articles/10.3389/feart.2018.00045'
FRACTIONS = {'¼': 0.25, '½': 0.5, '¾': 0.75}
RANGE_MARKERS = ('−', '–', '-')
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60


def cell_text(cell: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', cell))).strip()


def lead_hours(cell: str) -> float | None:
    """Return hours for a single stated time, or None for a range or an empty cell."""
    text = cell.strip('~() .').replace('min.', 'min')
    if not text or any(marker in text for marker in RANGE_MARKERS):
        return None
    days = re.fullmatch(r'(\d+) days', text)
    if days:
        return float(int(days.group(1)) * HOURS_PER_DAY)
    parts = re.fullmatch(r'(?:(\d+)\s*([¼½¾])?\s*h)?\s*(?:(\d+) min)?', text)
    if not parts or (parts.group(1) is None and parts.group(3) is None):
        raise ValueError(f'unrecognised precursor time: {cell!r}')
    hours = int(parts.group(1) or 0) + FRACTIONS.get(parts.group(2), 0)
    return round(hours + int(parts.group(3) or 0) / MINUTES_PER_HOUR, 4)


def parse_rows(page: str) -> list[dict]:
    table = re.search(r'(?is)<table.*?</table>', page).group(0)
    rows = []
    for row in re.findall(r'(?is)<tr.*?</tr>', table):
        cells = [cell_text(c) for c in re.findall(r'(?is)<t[dh].*?</t[dh]>', row)]
        if len(cells) != 7 or not cells[0].isdigit():
            continue
        year, eruption, date, warned, detected, visual, time = cells
        rows.append({
            'eruption': eruption,
            'year': int(year),
            'lead_hours': lead_hours(time),
            'source_url': SOURCE_URL,
            'quote_or_row': f'Iceland only. Table 1 row: {year} | {eruption} | {date} | '
                            f'W={warned} | D={detected} | V={visual} | T={time}',
        })
    return rows


def main() -> None:
    page = (ROOT / 'raw' / 'einarsson_2018.html').read_text(encoding='utf-8', errors='replace')
    rows = parse_rows(page)
    (ROOT / 'precursor_rows.json').write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    values = [r['lead_hours'] for r in rows if r['lead_hours'] is not None]
    print(f'{len(rows)} rows, {len(values)} with a value, range {min(values)} to {max(values)} h')


if __name__ == '__main__':
    main()
