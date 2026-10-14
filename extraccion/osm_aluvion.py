import osmium, json, re
PBF = "/home/lesterwood/ors-chile/files/chile-latest.osm.pbf"
S, N, W, E = -33.445, -33.365, -70.565, -70.415
NAMES = re.compile(r"Álvaro del Portillo|General Blanche|Quebrada Honda|La Plaza|Camino El Alba|^San Carlos de Apoquindo|Las Condesas|Colina Vista Hermosa|^San Ramón|Padre Hurtado|Francisco Bulnes|Paul Harris|Apoquindo", re.I)
out = {"calles": [], "cauces": [], "lugares": [], "edif_salud": []}
class H(osmium.SimpleHandler):
    def node(self, n):
        t = dict(n.tags)
        if not (S <= n.location.lat <= N and W <= n.location.lon <= E): return
        if t.get("place") or t.get("natural") == "peak" or t.get("amenity") in ("hospital", "clinic", "university"):
            if t.get("name"): out["lugares"].append({"name": t["name"], "k": t.get("place") or t.get("natural") or t.get("amenity"), "lat": n.location.lat, "lon": n.location.lon, "ele": t.get("ele")})
    def way(self, w):
        t = dict(w.tags); nm = t.get("name", "")
        isroad = "highway" in t and NAMES.search(nm or "")
        iswat = "waterway" in t or t.get("natural") in ("valley", "water")
        isinst = t.get("amenity") in ("hospital", "clinic", "university") and nm
        if not (isroad or iswat or isinst): return
        try: pts = [(n.lat, n.lon) for n in w.nodes]
        except osmium.InvalidLocationError: return
        if not any(S <= a <= N and W <= b <= E for a, b in pts): return
        rec = {"id": w.id, "name": nm, "k": t.get("waterway") or t.get("highway") or t.get("natural") or t.get("amenity"), "tunnel": t.get("tunnel"), "pts": pts}
        (out["calles"] if isroad else out["cauces"] if iswat else out["edif_salud"]).append(rec)
H().apply_file(PBF, locations=True, idx="flex_mem")
json.dump(out, open("/home/lesterwood/campos/aluvion/osm.json", "w"), ensure_ascii=False)
import collections
for k in out: print(k, len(out[k]), collections.Counter((r.get("k"), r.get("name")) for r in out[k]).most_common(40))
