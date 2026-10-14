# Severidad del incendio de dic-2025 en las cuencas aportantes (H1, S1, S2) con el índice dNBR de Sentinel-2 L2A (Key & Benson 2006):
# NBR = (B08 − B12)/(B08 + B12), dNBR = NBR_antes − NBR_después; RdNBR no se usa. Escenas sin nubes antes (2025-12-23; la más despejada entre el 20 y el 28 de diciembre) y después
# (2026-02-06) del incendio (29-dic-2025 a 2-ene-2026), leídas por ventana de los COG públicos (Earth Search, AWS). B12 (20 m) se remuestrea
# al cuadriculado de B08 (10 m) por vecino más cercano. Clases USGS/Key & Benson: <0,10 sin quemar; 0,10–0,27 baja; 0,27–0,44 moderada-baja;
# 0,44–0,66 moderada-alta; >0,66 alta. Cuencas en UTM 19S. Escribe validacion/incendio/dnbr_<tile>.tif, dnbr_resumen.json y dnbr.png.
import sys, json, urllib.request, numpy as np, rasterio
from rasterio.windows import from_bounds
from rasterio.warp import reproject, Resampling
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, transform as stf
from pyproj import Transformer
from rasterio.features import geometry_mask
sys.path.insert(0, 'fuentes'); from registrar import registrar
STAC = 'https://earth-search.aws.element84.com/v1'
def buscar(d0, d1):
    q = json.dumps({'collections': ['sentinel-2-l2a'], 'datetime': f'{d0}T00:00:00Z/{d1}T23:59:59Z', 'intersects': {'type': 'Point', 'coordinates': [-70.47, -33.40]}, 'limit': 50}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(STAC + '/search', q, {'Content-Type': 'application/json'}), timeout=60).read())
    return sorted(r['features'], key=lambda f: f['properties'].get('eo:cloud_cover', 100))
CU = {k: unary_union([shape(f['geometry']) for f in json.load(open(f'cuenca_{k}.geojson'))['features']]) for k in ('H1', 'S1', 'S2')}
TOT = unary_union(list(CU.values()))
def nbr(item, crs_dst=None):
    to = Transformer.from_crs(32719, item['properties']['proj:code'] if 'proj:code' in item['properties'] else f"EPSG:{item['properties']['proj:epsg']}", always_xy=True)
    g = stf(lambda x, y, z=None: to.transform(x, y), TOT); b = g.buffer(300).bounds
    with rasterio.open(item['assets']['nir']['href']) as d:
        w = from_bounds(*b, d.transform); n8 = d.read(1, window=w).astype(float); tr = d.window_transform(w); crs = d.crs
    with rasterio.open(item['assets']['swir22']['href']) as d:
        b12 = np.zeros_like(n8); reproject(rasterio.band(d, 1), b12, dst_transform=tr, dst_crs=crs, resampling=Resampling.nearest)
    with rasterio.open(item['assets']['scl']['href']) as d:
        scl = np.zeros(n8.shape, np.uint8); reproject(rasterio.band(d, 1), scl, dst_transform=tr, dst_crs=crs, resampling=Resampling.nearest)
    off = -1000 if item['properties'].get('earthsearch:boa_offset_applied') is False and item['properties'].get('s2:processing_baseline', '0') >= '04.00' else 0
    n8 = (n8 + off) / 1e4; b12 = (b12 + off) / 1e4
    return (n8 - b12) / np.maximum(n8 + b12, 1e-6), scl, tr, crs, to
pre = [f for f in buscar('2025-12-20', '2025-12-28') if '19HCD' in f['id']][0]
post = [f for f in buscar('2026-02-01', '2026-02-12') if '19HCD' in f['id']][0]
print('antes', pre['id'], pre['properties']['eo:cloud_cover'], '· después', post['id'], post['properties']['eo:cloud_cover'])
N0, S0, tr, crs, to = nbr(pre); N1, S1_, _, _, _ = nbr(post)
d = N0 - N1; malo = np.isin(S0, [0, 3, 8, 9, 10]) | np.isin(S1_, [0, 3, 8, 9, 10])
prof = {'driver': 'GTiff', 'height': d.shape[0], 'width': d.shape[1], 'count': 1, 'dtype': 'float32', 'crs': crs, 'transform': tr, 'compress': 'deflate', 'nodata': np.nan}
with rasterio.open('validacion/incendio/dnbr_19HCD.tif', 'w', **prof) as o: o.write(np.where(malo, np.nan, d).astype('float32'), 1)
CL = [('sin quemar', -9, 0.10), ('baja', 0.10, 0.27), ('moderada-baja', 0.27, 0.44), ('moderada-alta', 0.44, 0.66), ('alta', 0.66, 9)]
res = {'escena_antes': pre['id'], 'escena_despues': post['id'], 'pixel_m2': abs(tr.a * tr.e), 'cuencas': {}}
for k, g in list(CU.items()) + [('total', TOT)]:
    gu = stf(lambda x, y, z=None: to.transform(x, y), g)
    m = ~geometry_mask([mapping(gu)], d.shape, tr) & ~malo
    A = m.sum() * res['pixel_m2'] / 1e6; v = d[m]
    c = {n: round(float(((v >= a) & (v < b)).sum() * res['pixel_m2'] / 1e6), 3) for n, a, b in CL}
    res['cuencas'][k] = {'area_valida_km2': round(float(A), 3), 'dnbr_mediana': round(float(np.median(v)), 3), 'km2_por_clase': c,
                         'Bmh_km2': round(c['moderada-alta'] + c['alta'], 3), 'quemado_km2_dnbr_ge_0.10': round(sum(c[n] for n in c if n != 'sin quemar'), 3),
                         'sin_datos_frac': round(float((~geometry_mask([mapping(gu)], d.shape, tr) & malo).sum() / max(1, (~geometry_mask([mapping(gu)], d.shape, tr)).sum())), 3)}
json.dump(res, open('validacion/incendio/dnbr_resumen.json', 'w'), indent=1, ensure_ascii=False)
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
fig, ax = plt.subplots(figsize=(7, 5)); cm = ListedColormap(['#1a9850', '#fee08b', '#fdae61', '#f46d43', '#a50026'])
ext = (tr.c, tr.c + tr.a * d.shape[1], tr.f + tr.e * d.shape[0], tr.f)
im = ax.imshow(np.where(malo, np.nan, d), cmap=cm, norm=BoundaryNorm([-1, .1, .27, .44, .66, 1.5], 5), extent=ext)
for k, g in CU.items():
    gu = stf(lambda x, y, z=None: to.transform(x, y), g)
    for p in getattr(gu, 'geoms', [gu]): x, y = p.exterior.xy; ax.plot(x, y, 'k-', lw=0.8)
cb = fig.colorbar(im, ax=ax, ticks=[0, .185, .355, .55, .9]); cb.ax.set_yticklabels(['sin quemar', 'baja', 'mod.-baja', 'mod.-alta', 'alta'], fontsize=7)
ax.set_title(f"dNBR Sentinel-2 ({pre['id'][10:18]} → {post['id'][10:18]}) y cuencas aportantes", fontsize=8); ax.set_xticks([]); ax.set_yticks([])
fig.tight_layout(); fig.savefig('validacion/incendio/dnbr.png', dpi=150)
cb.ax.set_yticklabels(['unburned', 'low', 'mod.-low', 'mod.-high', 'high'], fontsize=7)
ax.set_title(f"dNBR Sentinel-2 ({pre['id'][10:18]} → {post['id'][10:18]}) and contributing basins", fontsize=8); fig.savefig('validacion/incendio/dnbr_en.png', dpi=150)
for it in (pre, post): registrar('archivo', 'validacion/incendio/dnbr_19HCD.tif', f"Sentinel-2 {it['id']} (B08, B12, SCL) leído por ventana para el dNBR del incendio dic-2025", 'validacion/incendio/dnbr_19HCD.tif')
print(json.dumps(res['cuencas'], ensure_ascii=False, indent=1))
