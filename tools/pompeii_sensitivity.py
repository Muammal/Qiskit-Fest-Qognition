"""Pompeii assumption tests: change one assumption at a time, five seeds each.

Settings are changed only in the worker running that job and restored after it.
The mind is never touched. Raw results used in docs/POMPEII_SOURCES.md are in
tools/pompeii_results/sensitivity.json.

Run from the project root:
    PYTHONPATH=. python tools/pompeii_sensitivity.py out.json
"""
import sys,json; sys.path.insert(0,'.')
from multiprocessing import Pool
from statistics import mean
import engine.pompeii as P, engine.citizens as C, engine.eruption as E
CONFIGS={
 'baseline':{},
 'collapse deaths 25%':{'P.COLLAPSE_DEATH_CHANCE':.25},
 'collapse deaths 100%':{'P.COLLAPSE_DEATH_CHANCE':1.},
 'roofs fail sooner (half by 1.9 m)':{'E.COLLAPSE_SPAN_M':1.8},
 'roofs fail later (20% by 2.8 m)':{'E.COLLAPSE_SPAN_M':9.},
 'notice chance x0.5':{'C.NEWS_BASE_CHANCE':.25},
 'notice chance x1.5':{'C.NEWS_BASE_CHANCE':.75},
 'indoors factor 0.25':{'C.INDOORS_FACTOR':.25},
 'servant relay x0.5':{'C.RELAY_BASE_CHANCE':.25},
 'pumice slowdown x2':{'C.PUMICE_SLOWDOWN_PER_M':1.},
 'pumice slowdown x4':{'C.PUMICE_SLOWDOWN_PER_M':2.},
 'tighter crowding (30/tile)':{'C.STREET_CROWD_PER_TILE':30},
 'tighter gates (200/step)':{'P.GATE_CROSSINGS_PER_STEP':200},
 'crowding off':{'kw.crowding':False},
 'quake off':{'kw.quake':False},
 'autumn':{'kw.date':'autumn'},
 'enslaved held with household':{'kw.restrict_enslaved':True},
 '20,000 people':{'kw.population':20000},
}
MODS={'P':P,'C':C,'E':E}
def one(job):
    name,mapping,mind,seed=job
    kw={}; saved=[]
    for k,v in CONFIGS[name].items():
        m,a=k.split('.')
        if m=='kw': kw[a]=v
        else:
            saved.append((MODS[m],a,getattr(MODS[m],a))); setattr(MODS[m],a,v)
    E._FORECAST_CACHE.clear()
    s=P.PompeiiSimulation(seed=seed,mind_type=mind,event_mapping=mapping,**kw); t17=t01=0
    while True:
        r=s.step()
        if r is None: break
        if r['t']==20: t17=r['counts']['in_town']
        if r['t']==52: t01=r['counts']['in_town']
    for mod,a,v in saved: setattr(mod,a,v)
    c=s.death_breakdown()['causes']; tb=s.outcome_table(); n=len(s.people)
    return dict(name=name,mapping=mapping,mind=mind,seed=seed,n=n,dead=len(s.deaths),roof=c.get('roof_collapse',0),flow=c.get('pyroclastic_flow',0),t17=t17,t01=t01,enslaved=tb['enslaved']['survived']/tb['enslaved']['total'],resident=tb['resident']['survived']/tb['resident']['total'],road=s.death_breakdown()['share_of_flow_deaths_on_roads'])
if __name__=='__main__':
    jobs=[(n,m,mi,s) for n in CONFIGS for m,mi in (('B','quantum'),('C','quantum'),('C','classical_mixture')) for s in range(1,6)]
    with Pool(5,maxtasksperchild=1) as p: rows=p.map(one,jobs,chunksize=1)
    json.dump(rows,open(sys.argv[1],'w'))
    for n in CONFIGS:
        for m,mi in (('B','quantum'),('C','quantum'),('C','classical_mixture')):
            R=[r for r in rows if r['name']==n and r['mapping']==m and r['mind']==mi]
            print(f"{n:36s} {m} {mi:18s} dead {round(mean(r['dead'] for r in R)):5d} ({min(r['dead'] for r in R)}-{max(r['dead'] for r in R)}) roof {round(mean(r['roof'] for r in R)):5d} flow {round(mean(r['flow'] for r in R)):5d} t17 {round(mean(r['t17'] for r in R)):5d} t01 {round(mean(r['t01'] for r in R)):5d} surv enslaved {mean(r['enslaved'] for r in R):.3f} resident {mean(r['resident'] for r in R):.3f}")
