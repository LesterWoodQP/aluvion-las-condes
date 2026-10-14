# Cuencas aportantes (v3, revisión A2 §4): DEM FABDEM reproyectado a UTM 19S a 30 m (D8 en metros), delimitación con los índices
# de celda que usa pysheds (sin reconstruirlos por truncamiento). Salidas: puntos donde cada cauce de OSM llega a la urbanización.
#   H1  cauce principal (Cerro El Gorila/quebradas altas) → abanico al sur del complejo deportivo
#   S1  cauce sur (Cerro Alto de las Vizcachas/El Banderín) → ducto en el borde urbano → campus U. de los Andes
#   S2  quebradas cortas que terminan en Av. La Plaza Sur frente a la Clínica U. de los Andes
#   H2  cruce del cauce entubado con Fco. Bulnes Correa (solo para referencia: aguas abajo de H1)
import json, numpy as np, rasterio
if not hasattr(np, "in1d"): np.in1d = np.isin   # pysheds con numpy 2
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pysheds.grid import Grid
from pyproj import Transformer
SRC = '/home/linuxoficina/Proyectos/dem/fabdem/S34W071_FABDEM_V1-2.tif'
fw = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True)
x0, y0 = fw.transform(-70.53, -33.445); x1, y1 = fw.transform(-70.41, -33.385); R = 30.0
W, H = int((x1 - x0) / R), int((y1 - y0) / R); tr = rasterio.transform.from_origin(x0, y1, R, R)
with rasterio.open(SRC) as d:
    dst = np.zeros((H, W), 'float32'); reproject(rasterio.band(d, 1), dst, dst_transform=tr, dst_crs='EPSG:32719', resampling=Resampling.bilinear)
with rasterio.open('dem/fabdem_utm30.tif', 'w', driver='GTiff', width=W, height=H, count=1, dtype='float32', crs='EPSG:32719', transform=tr, nodata=-9999) as o: o.write(dst, 1)
g = Grid.from_raster('dem/fabdem_utm30.tif'); dem = g.read_raster('dem/fabdem_utm30.tif')
fd = g.resolve_flats(g.fill_depressions(g.fill_pits(dem))); fdir = g.flowdir(fd); acc = g.accumulation(fdir)
A = np.asarray(acc); Z = np.asarray(dem)
SALIDAS = {'H1': (-33.40011, -70.49800), 'S1': (-33.40703, -70.49092), 'S2': (-33.40870, -70.49990), 'H2': (-33.40590, -70.51630),
           'QA': (-33.41717, -70.49227)}   # QA: quebrada Apoquindo–Los Almendros al entrar a la urbanización (Sernageomin RETERM 02/2026, fig. A)
out = {}
for k, (lat, lon) in SALIDAS.items():
    x, y = fw.transform(lon, lat)
    # salida = celda de mayor acumulación a ≤ 120 m del punto pedido (el cauce principal, no un canal menor vecino)
    c0, r0 = ~g.affine * (x, y); c0, r0 = int(np.floor(c0)), int(np.floor(r0)); kw = 4
    win = A[r0 - kw:r0 + kw + 1, c0 - kw:c0 + kw + 1]; rr, cc = np.unravel_index(np.argmax(win), win.shape); row, col = r0 - kw + rr, c0 - kw + cc
    xs, ys = g.affine * (col + 0.5, row + 0.5)
    cr = g.catchment(x=col, y=row, fdir=fdir, xytype='index'); c = np.asarray(cr, bool)
    z = Z[c]; zs = float(Z[row, col])
    import rasterio.features as rf
    poly = [s for s, v in rf.shapes(c.astype(np.uint8), mask=c, transform=g.affine) if v == 1]
    json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {'nombre': k}, 'geometry': p} for p in poly]}, open(f'cuenca_{k}.geojson', 'w'))
    out[k] = {'salida_pedida': [lat, lon], 'desplazamiento_ajuste_m': round(float(np.hypot(xs - x, ys - y)), 1), 'area_km2': round(c.sum() * R * R / 1e6, 3),
              'acumulacion_en_salida_celdas': int(A[row, col]), 'celdas_cuenca': int(c.sum()), 'z_max_m': round(float(z.max()), 1), 'z_salida_m': round(zs, 1),
              'relieve_R_m': round(float(z.max()) - zs, 1)}
json.dump(out, open('cuenca.json', 'w'), indent=1); print(json.dumps(out, indent=1))
