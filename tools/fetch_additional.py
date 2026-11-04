import sys,json,re,html
sys.path.insert(0,'tools')
import collect_disaster_data as c
pages=[('pelee_usgs','https://www.usgs.gov/news/volcano-watch-chronology-a-volcanic-disaster'),('heimaey_museum','https://safnahus.vestmannaeyjar.is/page/heimaey-the-eruption-1973'),('heimaey_wiki','https://en.wikipedia.org/wiki/Eldfell'),('la_palma_frontiers','https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2023.1166073/full'),('st_vincent_ipgp','https://www.ipgp.fr/actus-et-agenda/actualites/retour-sur-leruption-de-la-soufriere-de-saint-vincent-et-les-grenadines/'),('noaa_volcano_docs','https://www.ngdc.noaa.gov/hazard/volcano.shtml'),('noaa_tsunami_docs','https://www.ngdc.noaa.gov/hazard/tsu_db.shtml'),('noaa_volcano_fields','https://www.ngdc.noaa.gov/hazel/view/hazards/volcano/event-data?'),('brown_fatalities','https://static-content.springer-cdn.com/esm/art%3A10.1186%2Fs13617-017-0067-4/MediaObjects/13617_2017_67_MOESM1_ESM.xlsx'),('miyakejima_tokyo','https://www.eri.u-tokyo.ac.jp/KOHO/Yoran2001ep/05_2.html')]
for sid,url in pages:c.single(sid,url,sid+('.xlsx' if sid=='brown_fatalities' else '.html'))
(c.ROOT/'additional_manifest.json').write_text(json.dumps({'sources':c.SOURCES,'failures':c.FAILURES},indent=2))
for sid,url in pages:
 p=c.RAW/(sid+'.html')
 if p.exists():
  s=p.read_text(encoding='utf-8',errors='replace');s=re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>',' ',s);s=html.unescape(re.sub('<[^>]+>',' ',s));s=re.sub(r'\s+',' ',s);(c.RAW/(sid+'.txt')).write_text(s,encoding='utf-8')
