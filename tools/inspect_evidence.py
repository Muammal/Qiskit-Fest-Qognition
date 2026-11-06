from pathlib import Path
from html.parser import HTMLParser


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out = []
        self.skip = 0

    def handle_starttag(self, t, a):
        if t in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, t):
        if t in ("script", "style"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, s):
        if not self.skip:
            self.out.append(s)


r = Path("disaster_data/raw")
terms = {
    "pelee_wiki": ["leave", "governor", "April"],
    "pelee_usgs": ["May 8", "May 3", "May 5", "April"],
    "heimaey_wiki": ["21 January", "evacuat", "pyroclastic", "ash", "dioxide"],
    "heimaey_museum": ["evacuat", "1973"],
    "la_palma_frontiers": ["11 September", "19 September", "evacuat", "density currents", "eruption began"],
    "st_vincent_ipgp": ["2020", "12 avril", "2021"],
    "noaa_volcano_docs": ["agent", "database", "documentation"],
    "noaa_tsunami_docs": ["cause", "documentation"],
    "open_meteo_terms": ["CC BY", "Attribution", "license"],
    "ibtracs_terms": ["Knapp", "Gahtan", "Cite", "license"],
}
for name, tt in terms.items():
    p = r / (name + ".html")
    if not p.exists():
        continue
    parser = Text()
    parser.feed(p.read_text(encoding="utf-8", errors="replace"))
    s = " ".join(" ".join(parser.out).split())
    (r / (name + ".txt")).write_text(s, encoding="utf-8")
    print("\nPAGE", name, flush=True)
    for term in tt:
        start = 0
        for _ in range(2):
            i = s.lower().find(term.lower(), start)
            if i < 0:
                break
            print(s[max(0, i - 80) : i + 650], flush=True)
            start = i + len(term)
