import osmium, json
PBF = "/home/lesterwood/ors-chile/files/chile-latest.osm.pbf"
S, N, W, E = -33.425, -33.380, -70.545, -70.470
out = []
class H(osmium.SimpleHandler):
    def area(self, a):
        t = dict(a.tags)
        if "building" not in t and t.get("landuse") not in ("residential",) and t.get("leisure") not in ("park",) and t.get("amenity") not in ("parking",): return
        for o in a.outer_rings():
            try: ring = [(n.lat, n.lon) for n in o]
            except osmium.InvalidLocationError: continue
            if not any(S <= la <= N and W <= lo <= E for la, lo in ring): continue
            out.append({"k": "building" if "building" in t else (t.get("landuse") or t.get("leisure") or t.get("amenity")), "lv": t.get("building:levels"), "h": t.get("height"), "name": t.get("name"), "ring": ring})
H().apply_file(PBF, locations=True, idx="flex_mem")
json.dump(out, open("/home/lesterwood/campos/aluvion/edificios.json", "w"), ensure_ascii=False)
import collections; print(len(out), collections.Counter(o["k"] for o in out).most_common(6), "con pisos:", sum(1 for o in out if o["lv"]))
