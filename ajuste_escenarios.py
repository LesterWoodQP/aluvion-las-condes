# % de ajuste de cada escenario del visor con lo observado: promedio de los cuatro componentes de los criterios fijados de antemano
# (sección de calibración del paper), cada uno en [0, 1]:
#   calles = R_presencia (fracción de puntos de calles con barro observado que el modelo moja, h > 5 cm)
#   sitios = fracción de sitios con afectación confirmada alcanzados
#   alcance = 1 si el barro llega a ≤ 200 m de Padre Hurtado; baja linealmente hasta 0 a 1.200 m
#   precision = fracción del barro simulado en zona urbana (≤ 40 m de un edificio) que cae dentro de la zona afectada oficial
#               (IDE Chile / Bienes Nacionales, 11-oct-2026); antes se usaba el perímetro publicado por la prensa
# Escribe "ajuste" en web/esc/index.json (y la copia del sitio).
import csv, json, shutil, numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import shape
from shapely import contains_xy
from shapely.ops import transform as stf
from pyproj import Transformer
_tf = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True).transform
ZONA = stf(_tf, shape(json.load(open('fuentes/visor_bbnn/zona_afectada.geojson'))['features'][0]['geometry']))
_B = json.load(open('bloques_v4.json')); _tb = cKDTree(np.c_[[b['cx'] for b in _B], [b['cy'] for b in _B]])
def perimetro_oficial(corrida):
    d = np.load(f'res/{corrida}.npz'); m = d['hmax'] > 0.05; X, Y, A = d['cx'][m], d['cy'][m], d['area'][m]
    u = _tb.query(np.c_[X, Y])[0] <= 40; return float(A[u & contains_xy(ZONA, X, Y)].sum() / max(A[u].sum(), 1))
CORR = {'v4lluviamedida': 'p34b', 'v4campusfino': 'm36', 'v4sinincendio': 'f35b', 'v4sinincendiofluido': 'f38b', 'v4lineaarboles': 'arc', 'v4tapon': 'art', 'v4integrada': 'v32', 'v4porosas': 'z26', 'v4faldeo': 'z29', 'v4lluvia': 'v02', 'v4cauce': 'v01', 'v4brazosur': 'v19', 'v4sinlluvia': 'v21', 'v4col100': 'v10', 'v4col30': 'v17', 'v14': 'v14', 'v16': 'v16', 'mejor': 'e04', 'ladera': 'f03', 'cauce150': 'f01', 'colector30': 'k01', 'espeso': 'e06', 'h4': 'e01', 'h1': 'd04', 'h3': 'd02', 'h2': 'e03'}
M = {r['corrida'][:-4]: r for r in csv.DictReader(open('res/corridas.csv')) if r['hstar'] == '0.05'}
idx = json.load(open('web/esc/index.json'))
for e in idx:
    r = M[CORR[e['id']]]; R, S, d, P = float(r['R_presencia']), float(r['S_sitios']), float(r['dist_PH_m']), float(r['P'])
    comp = {'calles': R, 'sitios': S, 'alcance': max(0.0, min(1.0, 1 - (d - 200) / 1000)), 'precision': perimetro_oficial(CORR[e['id']])}
    e['ajuste'] = round(100 * sum(comp.values()) / 4); e['criterios'] = int(R >= 0.6) + int(S >= 0.75) + int(d <= 200) + int(comp['precision'] >= 0.5)
    e['componentes'] = {k: round(v, 2) for k, v in comp.items()}; e['corrida'] = CORR[e['id']]
    e['etiqueta'] = e['etiqueta'].replace('Mejor ajuste · ', ''); e['etiqueta'] = e['etiqueta'][0].upper() + e['etiqueta'][1:]
    print(e['id'], e['corrida'], e['ajuste'], '%', e['criterios'], '/4', e['componentes'])
json.dump(idx, open('web/esc/index.json', 'w'), ensure_ascii=False)
shutil.copy('web/esc/index.json', 'sitio/visor/esc/index.json')
