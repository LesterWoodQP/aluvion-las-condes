# Evalúa las microsimulaciones del campus U. Andes: barro junto a la Biblioteca (anillo de 20 m alrededor de su huella OSM),
# dentro de su cuenca local (cuenca_biblioteca.geojson) y área con h > 5 cm. Escribe validacion/micro_campus.json.
import sys, json, glob, os, numpy as np
from shapely.geometry import shape, Polygon
from shapely.ops import transform as stf
from shapely import contains_xy
from pyproj import Transformer
tf = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True).transform
el = next(e for e in json.load(open('fuentes/overpass_biblioteca.json'))['elements'] if e.get('tags', {}).get('name') == 'Biblioteca')
B = stf(tf, Polygon([(p['lon'], p['lat']) for p in el['geometry']])) if 'geometry' in el else stf(tf, shape({'type': 'Point', 'coordinates': [el['center']['lon'], el['center']['lat']]})).buffer(25)
ANILLO = B.buffer(20).difference(B); CU = stf(tf, shape(json.load(open('cuenca_biblioteca.geojson'))['features'][0]['geometry']))
PV = json.load(open('validacion/patio_video.json')); PX, PY = Transformer.from_crs(4326, 32719, always_xy=True).transform(PV['lon'], PV['lat'])   # patio del video (Lester)
out = json.load(open('validacion/micro_campus.json')) if os.path.exists('validacion/micro_campus.json') else {}
for f in sys.argv[1:] or sorted(glob.glob('res/m*.npz')):
    d = np.load(f); x, y, h, A, v = d['cx'], d['cy'], d['hmax'], d['area'], d['vmax']; cid = os.path.basename(f)[:-4]
    ia = contains_xy(ANILLO, x, y); ic = contains_xy(CU, x, y); m = h > 0.05
    out[cid] = {'h_max_anillo_biblioteca_m': round(float(h[ia].max()), 3) if ia.any() else None, 'frac_anillo_h5cm': round(float(A[ia & m].sum() / A[ia].sum()), 3) if ia.any() else None,
                'ha_h5cm_cuenca_local': round(float(A[ic & m].sum() / 1e4), 2), 'ha_h5cm_total': round(float(A[m].sum() / 1e4), 2), 'h_max_m': round(float(h.max()), 2), 'h_max_patio_video_15m': round(float(h[np.hypot(x - PX, y - PY) <= 15].max()), 3), 'v_max_ms': round(float(v.max()), 1),
                'params': json.loads(str(d['params'])) if 'params' in d.files else None}
    print(cid, {k: v_ for k, v_ in out[cid].items() if k != 'params'})
json.dump(out, open('validacion/micro_campus.json', 'w'), ensure_ascii=False, indent=1)
