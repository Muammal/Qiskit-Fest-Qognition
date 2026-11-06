import sys
import json

sys.path.insert(0, "tools")
import collect_disaster_data as c

for kind in ["Volcanoes", "Eruptions"]:
    url = (
        "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows?service=WFS&version=2.0.0&request=GetFeature&typeName=GVP-VOTW:Smithsonian_VOTW_Holocene_"
        + kind
        + "&outputFormat=application/json"
    )
    c.single("gvp_" + kind.lower(), url, "gvp_" + kind.lower() + ".json")
for vn in [360150, 372010, 360120, 282040, 282060, 383010, 360050, 243040]:
    c.single("gvp_case_" + str(vn), "https://volcano.si.edu/volcano.cfm?vn=" + str(vn), "gvp_case_" + str(vn) + ".html")
c.single("einarsson_2018", "https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2018.00045/full", "einarsson_2018.html")
(c.ROOT / "supplemental_manifest.json").write_text(json.dumps({"sources": c.SOURCES, "failures": c.FAILURES}, indent=2))
