# Cruce de corridas con hechos de prensa del 9–10 oct 2026 (ver registro_consultas.jsonl): área afectada (200 ha balance municipal
# noche 8-oct; 253 ha Inciti) y lugares con ingreso de barro/agua reportado. Profundidad máxima a ≤ 40 m de cada punto.
import sys, json, numpy as np
from scipy.spatial import cKDTree
from pyproj import Transformer
tf = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True); U = lambda la, lo: tf.transform(lo, la)
LUG = {'UC Christus (~1 m urgencias)': (-33.40014, -70.50874), 'Duoc UC (personas atrapadas)': (-33.40063, -70.5054),
       'Campus U. Andes (barro, atrapados)': (-33.40424, -70.5066), 'Clínica U. Andes (ingreso menor de agua)': (-33.40727, -70.50373),
       'Hospital FACh (agua en urgencias)': (-33.39636, -70.54707)}
out = {}
for f in sys.argv[1:]:
    r = np.load(f); xy = np.c_[r['cx'], r['cy']]; h = r['hmax']; A = r['area']; t = cKDTree(xy)
    o = {'area_ha_h>2cm': round(float(A[h > 0.02].sum() / 1e4), 1), 'area_ha_h>5cm': round(float(A[h > 0.05].sum() / 1e4), 1)}
    for k, (la, lo) in LUG.items():
        ii = t.query_ball_point(U(la, lo), 40); o[k] = round(float(h[ii].max()), 2) if ii else None
    out[f.split('/')[-1][:-4]] = o; print(f.split('/')[-1][:-4], o)
json.dump(out, open('validacion/cruce_prensa_20261010.json', 'w'), indent=1, ensure_ascii=False)
