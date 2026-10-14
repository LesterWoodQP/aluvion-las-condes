# Preparación del terreno para la simulación del aluvión de Las Condes (8-oct-2026).
# - DTM: FABDEM V1-2 (Copernicus GLO-30 sin edificios ni vegetación), 1" (~30 m). Licencia CC BY-NC-SA 4.0 (uso no comercial).
# - DSM: Copernicus GLO-30 (con edificios y vegetación), 1".
# - Edificios: plantas de OpenStreetMap. Altura por bloque = estadísticas de (DSM − DTM) dentro de la planta; si la planta
#   es más chica que la celda de 30 m o la diferencia no es fiable, se usa building:levels × 3 m o 6 m (casa de 2 pisos).
# - Calles: se rebajan 0,15 m de cordón a cordón (ancho por tipo de vía): son los canales por donde corre el barro.
# Salida: terreno.npz (grilla UTM 19S de 4 m) y edificios.json (planta, altura media/máxima, fuente).
import json, math, numpy as np, rasterio
from rasterio.warp import transform as rtransform
from scipy import ndimage as nd
from PIL import Image, ImageDraw
from pyproj import Transformer

LON0, LON1, LAT0, LAT1 = -70.553, -70.490, -33.421, -33.391
DX = 4.0
tf = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True)
inv = Transformer.from_crs('EPSG:32719', 'EPSG:4326', always_xy=True)
xs, ys = tf.transform([LON0, LON1, LON0, LON1], [LAT0, LAT0, LAT1, LAT1])
X0, X1, Y0, Y1 = math.floor(min(xs)), math.ceil(max(xs)), math.floor(min(ys)), math.ceil(max(ys))
NX, NY = int((X1 - X0) / DX), int((Y1 - Y0) / DX)
gx = X0 + (np.arange(NX) + 0.5) * DX; gy = Y0 + (np.arange(NY) + 0.5) * DX
GX, GY = np.meshgrid(gx, gy)                       # fila 0 = sur
LON, LAT = inv.transform(GX, GY)

def sample(path):
    with rasterio.open(path) as d:
        a = d.read(1).astype(np.float64); tr = ~d.transform
        c, r = tr * (LON, LAT)
        return nd.map_coordinates(a, [r - 0.5, c - 0.5], order=1, mode='nearest')
DTM = sample('/home/linuxoficina/Proyectos/dem/fabdem/S34W071_FABDEM_V1-2.tif')
DSM = sample('dem/cop_dsm_S34W071.tif')
print(f'grilla {NX}×{NY} a {DX} m · DTM {DTM.min():.0f}–{DTM.max():.0f} m · DSM−DTM medio {np.mean(DSM - DTM):.1f} m')

def to_px(lat, lon):
    x, y = tf.transform(lon, lat); return ((x - X0) / DX, (Y0 + NY * DX - y) / DX)   # imagen: fila 0 = norte (corrección A1 §6: borde real de la grilla)
def raster_poly(rings, S=1):
    im = Image.new('L', (NX * S, NY * S), 0); g = ImageDraw.Draw(im)
    for ring in rings: g.polygon([(px * S, py * S) for px, py in (to_px(a, b) for a, b in ring)], fill=255)
    m = np.array(im.resize((NX, NY), Image.BILINEAR)) > 127
    return m[::-1]                                  # fila 0 = sur

# ---------- calles (rebaje de 0,15 m)
o = json.load(open('osm.json'))
ANCHO = {'primary': 18, 'secondary': 14, 'tertiary': 11, 'residential': 8, 'living_street': 6, 'service': 5, 'unclassified': 7}
im = Image.new('L', (NX, NY), 0); g = ImageDraw.Draw(im)
for c in o['calles']:
    w = ANCHO.get(c['k']);
    if not w: continue
    g.line([to_px(a, b) for a, b in c['pts']], fill=255, width=max(1, int(round(w / DX))))
CALLE = (np.array(im) > 127)[::-1]

# ---------- edificios
E = json.load(open('edificios.json'))
DIFF = nd.median_filter(DSM - DTM, 3)
blocks = []; BH = np.zeros_like(DTM); excluidos = []
for e in E:
    if e['k'] != 'building' or len(e['ring']) < 4: continue
    m = raster_poly([e['ring']], S=2)
    n = int(m.sum())
    if n == 0: continue
    area = n * DX * DX; d = DIFF[m]
    # contornos de recintos etiquetados como edificio (complejos deportivos, clubes): no son volúmenes sólidos — se excluyen
    nom = (e.get('name') or '').lower()
    if (area > 20000 and float(np.mean(d)) < 4.0) or (area > 5000 and any(k in nom for k in ('complejo', 'club', 'cancha', 'parque'))):
        excluidos.append({'name': e.get('name'), 'area_m2': round(area), 'dsm_dtm_medio': round(float(np.mean(d)), 1)}); continue
    lv = None
    try: lv = float(str(e.get('lv') or '').replace(',', '.'))
    except ValueError: pass
    hm, hx = float(np.mean(d)), float(np.percentile(d, 95))
    if area >= 900 and hm > 2.5: h, src = float(np.clip(hm, 3, 45)), 'DSM−DTM (Copernicus − FABDEM)'
    elif lv: h, src = float(np.clip(lv * 3.0, 3, 45)), 'OSM building:levels × 3 m'
    else: h, src = 6.0, 'supuesto: casa de 2 pisos'
    BH[m] = np.maximum(BH[m], h)
    ys_, xs_ = np.nonzero(m)
    blocks.append({'name': e.get('name'), 'ring': e['ring'], 'area_m2': round(area), 'h': round(h, 1),
                   'dsm_dtm_medio': round(hm, 1), 'dsm_dtm_p95': round(hx, 1), 'fuente': src,
                   'cx': float(gx[int(xs_.mean())]), 'cy': float(gy[int(ys_.mean())])})
ELEV = DTM - 0.15 * CALLE + BH                       # terreno + bloques (las calles quedan como canales)
np.savez_compressed('terreno.npz', X0=X0, Y0=Y0, DX=DX, NX=NX, NY=NY, DTM=DTM.astype(np.float32), DSM=DSM.astype(np.float32),
                    ELEV=ELEV.astype(np.float32), BH=BH.astype(np.float32), CALLE=CALLE)
json.dump(blocks, open('bloques.json', 'w')); json.dump(excluidos, open('bloques_excluidos.json', 'w'), ensure_ascii=False, indent=1)
print('excluidos (recintos, no edificios):', excluidos)
hs = np.array([b['h'] for b in blocks]); src = {}
for b in blocks: src[b['fuente']] = src.get(b['fuente'], 0) + 1
print(f'bloques {len(blocks)} · altura media {hs.mean():.1f} m, máx {hs.max():.1f} m · fuentes {src}')
print(f'calles {int(CALLE.sum()) * DX * DX / 1e4:.1f} ha · UTM X {X0}–{X1}, Y {Y0}–{Y1}')
