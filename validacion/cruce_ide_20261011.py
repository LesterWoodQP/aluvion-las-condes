# Cruce de corridas con las capas oficiales del visor de emergencia (IDE Chile / Bienes Nacionales, 11-oct-2026):
# zona afectada (polígono), 2.266 predios afectados y 368 tramos de ejes viales afectados. Uso solo agregado (sin datos de predios).
#   predios: un predio cuenta como «con barro» si alguna celda del modelo con h > 5 cm cae en el predio ampliado 6 m (vereda/calle).
#   ejes: un tramo cuenta como «con barro» si ≥ 30 % de puntos cada 10 m tiene h > 5 cm a ≤ 8 m.
import sys, json, numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import shape
from shapely.ops import transform as stf
from shapely import contains_xy
from pyproj import Transformer
tf = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True).transform
D = 'fuentes/visor_bbnn/'
Z = stf(tf, shape(json.load(open(D + 'zona_afectada.geojson'))['features'][0]['geometry']))
PR = [stf(tf, shape(f['geometry'])) for f in json.load(open(D + 'predios_afectados.geojson'))['features']]
EJ = [stf(tf, shape(f['geometry'])) for f in json.load(open(D + 'ejes_viales_afectados.geojson'))['features']]
print(f'zona oficial {Z.area / 1e4:.1f} ha · predios {len(PR)} ({sum(p.area for p in PR) / 1e4:.1f} ha) · ejes {len(EJ)} ({sum(e.length for e in EJ) / 1000:.1f} km)')
inZ = sum(Z.buffer(5).contains(p.representative_point()) for p in PR); print(f'predios dentro de la zona oficial: {inZ}/{len(PR)}')
out = {}
for f in sys.argv[1:]:
    r = np.load(f); m = r['hmax'] > 0.05; X, Y, A = r['cx'][m], r['cy'][m], r['area'][m]; t = cKDTree(np.c_[X, Y])
    def moj(g, b):
        gb = g.buffer(b); x0, y0, x1, y1 = gb.bounds; c = ((x0 + x1) / 2, (y0 + y1) / 2); rad = np.hypot(x1 - x0, y1 - y0) / 2
        ii = t.query_ball_point(c, rad); return bool(ii) and bool(contains_xy(gb, X[ii], Y[ii]).any())
    pm = sum(moj(p, 6) for p in PR)
    em = 0
    for e in EJ:
        n = max(2, int(e.length / 10)); pts = [e.interpolate(i / (n - 1), normalized=True) for i in range(n)]
        d, _ = t.query(np.array([[p.x, p.y] for p in pts])); em += (np.mean(d <= 8) >= 0.3)
    dentro = contains_xy(Z, X, Y); a_in = A[dentro].sum() / 1e4; a = A.sum() / 1e4
    o = {'predios_con_barro': pm, 'frac_predios': round(pm / len(PR), 3), 'ejes_con_barro': int(em), 'frac_ejes': round(float(em) / len(EJ), 3),
         'area_mojada_ha': round(float(a), 1), 'frac_area_en_zona': round(float(a_in / a), 3), 'cobertura_zona': round(float(a_in / (Z.area / 1e4)), 3)}
    out[f.split('/')[-1][:-4]] = o; print(f.split('/')[-1][:-4], o, flush=True)
import os
if os.path.exists('validacion/cruce_ide_20261011.json'): _p = json.load(open('validacion/cruce_ide_20261011.json'))['corridas']; _p.update(out); out = _p   # agrega, no reemplaza
json.dump({'zona_ha': round(Z.area / 1e4, 1), 'n_predios': len(PR), 'n_ejes': len(EJ), 'corridas': out}, open('validacion/cruce_ide_20261011.json', 'w'), indent=1)
