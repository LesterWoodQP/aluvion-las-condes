# Terreno v4: dominio ampliado al suroeste (Hospital Dipreca, Paul Harris, Rotonda Atenas) y edificios completos.
# - Edificios: huellas de Overture Maps (release 2026-09-23.1: OpenStreetMap + Microsoft ML Buildings + Google Open Buildings; ODbL),
#   42.018 huellas, frente a 1.103 de OpenStreetMap en la versión anterior (que dejaba barrios enteros como terreno abierto).
# - Altura: media de (DSM − DTM) si la huella ≥ 900 m² y la diferencia > 2,5 m; si la huella es de OSM con building:levels, pisos × 3 m;
#   si no, 6 m (casa de dos pisos). Se excluyen los recintos identificados en v3 (complejos deportivos, centro comercial).
# - Calles rebajadas 0,15 m como en v3; terreno FABDEM a 4 m; opcionalmente cauce del parque lineal tallado.
# Salida: terreno_v4.npz y bloques_v4.json (sin la geometría completa: centroide, área, altura, fuente).
import json, math, sys, numpy as np, rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from scipy import ndimage as nd
from shapely.geometry import shape, Point
from shapely.ops import transform as stf
from shapely.strtree import STRtree
from PIL import Image, ImageDraw
from pyproj import Transformer
LON0, LON1, LAT0, LAT1 = -70.560, -70.490, -33.428, -33.391
DX = 4.0
tf = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True); inv = Transformer.from_crs('EPSG:32719', 'EPSG:4326', always_xy=True)
xs, ys = tf.transform([LON0, LON1, LON0, LON1], [LAT0, LAT0, LAT1, LAT1])
X0, X1, Y0, Y1 = math.floor(min(xs)), math.ceil(max(xs)), math.floor(min(ys)), math.ceil(max(ys))
NX, NY = int((X1 - X0) / DX), int((Y1 - Y0) / DX)
gx = X0 + (np.arange(NX) + 0.5) * DX; gy = Y0 + (np.arange(NY) + 0.5) * DX
GX, GY = np.meshgrid(gx, gy); LON, LAT = inv.transform(GX, GY)   # fila 0 = sur
def sample(path):
    with rasterio.open(path) as d:
        a = d.read(1).astype(np.float64); c, r = ~d.transform * (LON, LAT)
        return nd.map_coordinates(a, [r - 0.5, c - 0.5], order=1, mode='nearest')
DTM = sample('/home/linuxoficina/Proyectos/dem/fabdem/S34W071_FABDEM_V1-2.tif'); DSM = sample('dem/cop_dsm_S34W071.tif')
TRN = from_origin(X0, Y1, DX, DX)          # raster con fila 0 = norte; se invierte al final
def ras(geoms_vals, fill=0, dtype='float32'):
    return rasterize(geoms_vals, out_shape=(NY, NX), transform=TRN, fill=fill, dtype=dtype, all_touched=False)[::-1]
# calles
o = json.load(open('osm.json')); ANCHO = {'primary': 18, 'secondary': 14, 'tertiary': 11, 'residential': 8, 'living_street': 6, 'service': 5, 'unclassified': 7}
from shapely.geometry import LineString
lin = []
for c in o['calles']:
    w = ANCHO.get(c['k'])
    if not w or len(c['pts']) < 2: continue
    L = LineString([tf.transform(b, a) for a, b in c['pts']]); lin.append((L.buffer(w / 2, cap_style=2), 1))
CALLE = ras(lin, dtype='uint8').astype(bool)
# edificios
F = json.load(open('dem/overture/edificios.geojson'))['features']
G = [stf(tf.transform, shape(f["geometry"])) for f in F]
EXCL = [Point(*tf.transform(lo, la)).buffer(60) for la, lo in ((-33.4146118, -70.541851), (-33.3962327, -70.5041277), (-33.3961327, -70.5018604), (-33.3972332, -70.5013532))]
osm = json.load(open('edificios.json')); lv_pts = []
for e in osm:
    try: lv = float(str(e.get('lv') or '').replace(',', '.'))
    except ValueError: lv = None
    if lv and len(e.get('ring', [])) >= 3:
        x, y = tf.transform(np.mean([q[1] for q in e['ring']]), np.mean([q[0] for q in e['ring']])); lv_pts.append((Point(x, y), lv))
tree = STRtree([p for p, _ in lv_pts]) if lv_pts else None
ID = ras([(g, i + 1) for i, g in enumerate(G) if g.area > 0], dtype='int32')
DIFF = nd.median_filter(DSM - DTM, 3); idv = ID.ravel()
cnt = np.bincount(idv, minlength=len(G) + 1); sm = np.bincount(idv, weights=DIFF.ravel(), minlength=len(G) + 1)
H = np.zeros(len(G) + 1); src = {}; bloques = []
for i, g in enumerate(G):
    a = g.area; c = g.centroid; k = i + 1
    if any(c.within(z) for z in EXCL) and a > 5000: continue
    hm = sm[k] / cnt[k] if cnt[k] else 0.0; lv = None
    if tree is not None and F[i]['properties']['fuente'] == 'OpenStreetMap':
        j = tree.nearest(c); p, l = lv_pts[j]
        if p.distance(c) < 5: lv = l
    if a >= 900 and hm > 2.5: h, s_ = float(np.clip(hm, 3, 45)), 'DSM−DTM'
    elif lv: h, s_ = float(np.clip(lv * 3, 3, 45)), 'pisos OSM'
    else: h, s_ = 6.0, 'supuesto 6 m'
    H[k] = h; src[s_] = src.get(s_, 0) + 1
    bloques.append({'cx': round(c.x, 1), 'cy': round(c.y, 1), 'a': round(a, 1), 'h': round(h, 1), 'f': s_, 'o': F[i]['properties']['fuente']})
BH = H[ID]; BH[ID == 0] = 0.0
ELEV = DTM - 0.15 * CALLE + BH
np.savez_compressed('terreno_v4.npz', X0=X0, Y0=Y0, DX=DX, NX=NX, NY=NY, DTM=DTM.astype(np.float32), DSM=DSM.astype(np.float32),
                    ELEV=ELEV.astype(np.float32), BH=BH.astype(np.float32), CALLE=CALLE)
json.dump(bloques, open('bloques_v4.json', 'w'))
print(f'grilla {NX}×{NY} · bloques {len(bloques)} · fuentes de altura {src} · ocupación media {float((BH > 0).mean()) * 100:.1f} % · calles {CALLE.sum() * DX * DX / 1e4:.0f} ha')
