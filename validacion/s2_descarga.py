# Descarga recortada (lectura por ventanas de los COG públicos) de escenas Sentinel-2 L2A para la validación independiente.
# Bandas B02 B03 B04 B08 B11 B12 SCL al área de estudio (+200 m); informa la fracción local de nubes/sombras (SCL 3,8,9,10).
# Uso: python validacion/s2_descarga.py <id_item> [...]
import sys, json, urllib.request, os, numpy as np, rasterio
from rasterio.windows import from_bounds
sys.path.insert(0, 'fuentes'); from registrar import registrar
T = np.load('terreno.npz'); X0, Y0, DX, NX, NY = [float(T[k]) for k in ('X0', 'Y0', 'DX', 'NX', 'NY')]
B = (X0 - 200, Y0 - 200, X0 + NX * DX + 200, Y0 + NY * DX + 200)
os.makedirs('validacion/s2', exist_ok=True)
for iid in sys.argv[1:]:
    it = json.loads(urllib.request.urlopen(f'https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/{iid}', timeout=60).read())
    out = {}
    for b, k in (('blue', 'B02'), ('green', 'B03'), ('red', 'B04'), ('nir', 'B08'), ('swir16', 'B11'), ('swir22', 'B12'), ('scl', 'SCL')):
        with rasterio.open(it['assets'][b]['href']) as d:
            w = from_bounds(*B, d.transform); a = d.read(1, window=w); prof = d.profile | {'width': a.shape[1], 'height': a.shape[0], 'transform': d.window_transform(w), 'driver': 'GTiff', 'compress': 'deflate'}
            prof.pop('blockxsize', None); prof.pop('blockysize', None); prof.pop('tiled', None)
            with rasterio.open(f'validacion/s2/{iid}_{k}.tif', 'w', **prof) as o: o.write(a, 1)
            out[k] = a
    scl = out['SCL']; nub = float(np.isin(scl, [3, 8, 9, 10]).mean()); nodata = float((scl == 0).mean())
    json.dump(it, open(f'validacion/s2/{iid}.json', 'w'))
    registrar('archivo', f'validacion/s2/{iid}_SCL.tif', f'Sentinel-2 {iid} recortado al área: nubes/sombras locales {nub:.1%}, sin datos {nodata:.1%}', f'validacion/s2/{iid}_SCL.tif')
    print(iid, 'nubes/sombras locales', f'{nub:.1%}', 'sin datos', f'{nodata:.1%}', 'clases SCL', np.unique(scl, return_counts=True))
