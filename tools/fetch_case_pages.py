import sys,json,re,html
sys.path.insert(0,'tools')
import collect_disaster_data as c
pages=[('st_vincent_paper','https://www.nature.com/articles/s41467-022-31901-4'),('st_vincent_plumes','https://acp.copernicus.org/articles/23/15209/2023/acp-23-15209-2023.html'),('heimaey_usgs','https://pubs.usgs.gov/gip/heimaey/'),('pelee_paper','https://www.sciencedirect.com/science/article/pii/0377027389900309'),('pelee_wiki','https://en.wikipedia.org/wiki/1902_eruption_of_Mount_Pel%C3%A9e'),('montserrat_chronology','https://www.geo.mtu.edu/volcanoes/west.indies/soufriere/govt/miscdocs/chronology.html'),('montserrat_mvo','https://geo.mtu.edu/volcanoes/west.indies/soufriere/govt/scireps/mvo_report0018.html'),('la_palma_paper','https://www.nature.com/articles/s41598-022-23998-w'),('la_palma_wiki','https://en.wikipedia.org/wiki/2021_Cumbre_Vieja_volcanic_eruption'),('miyakejima_usgs','https://pubs.usgs.gov/publication/70206022'),('miyakejima_gsj','https://www.gsj.jp/hazards/volcano/miyake2000/'),('miyakejima_wiki','https://en.wikipedia.org/wiki/Miyake-jima')]
for sid,url in pages:c.single(sid,url,sid+'.html')
(c.ROOT/'evidence_manifest.json').write_text(json.dumps({'sources':c.SOURCES,'failures':c.FAILURES},indent=2))
for sid,url in pages:
    p=c.RAW/(sid+'.html')
    if p.exists():
        s=p.read_text(encoding='utf-8',errors='replace');s=re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>',' ',s);s=html.unescape(re.sub('<[^>]+>',' ',s));s=re.sub(r'\s+',' ',s)
        (c.RAW/(sid+'.txt')).write_text(s,encoding='utf-8')
