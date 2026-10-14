# Nube de puntos fotogramétrica SPOT 2014 de Santiago (Hussain 2021, OpenTopography OTDS.022021.32719.2, CC BY 4.0), formato EPT.
# Descarga solo los nodos del octree que intersectan el área de estudio (+300 m), filtra los puntos y genera:
#   dem/spot2014/dsm_min_5m.tif : mínimo z por celda de 5 m (superficie, incluye edificios y árboles)
#   dem/spot2014/puntos.npz     : x, y, z en UTM 19S dentro del área
import json, os, io, urllib.request, numpy as np, laspy
from concurrent.futures import ThreadPoolExecutor
B = 'https://opentopography.s3.sdsc.edu/dataspace/OTDS.022021.32719.2/ept/'
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'estudio-aluvion/1.0'}), timeout=120).read()
ept = json.loads(get(B + 'ept.json')); print('srs', ept.get('srs', {}).get('horizontal'), 'bounds', ept['bounds'], 'span', ept['span'])
T = np.load('terreno.npz'); X0, Y0, DX, NX, NY = [float(T[k]) for k in ('X0', 'Y0', 'DX', 'NX', 'NY')]
bx = (X0 - 300, Y0 - 300, X0 + NX * DX + 300, Y0 + NY * DX + 300)
b0 = ept['bounds']
def nb(d, x, y, z):
    s = (b0[3] - b0[0]) / 2 ** d
    return (b0[0] + x * s, b0[1] + y * s, b0[0] + (x + 1) * s, b0[1] + (y + 1) * s)
def hier(key):
    return json.loads(get(B + f'ept-hierarchy/{key}.json'))
H = hier('0-0-0-0'); nodos = []; pend = list(H.items())
while pend:
    k, n = pend.pop(); d, x, y, z = map(int, k.split('-')); a = nb(d, x, y, z)
    if a[2] < bx[0] or a[0] > bx[2] or a[3] < bx[1] or a[1] > bx[3]: continue
    if n == -1: pend += list(hier(k).items()); continue
    if n > 0: nodos.append(k)
print('nodos a bajar', len(nodos))
os.makedirs('dem/spot2014/laz', exist_ok=True)
def bajar(k):
    f = f'dem/spot2014/laz/{k}.laz'
    if not os.path.exists(f): open(f, 'wb').write(get(B + f'ept-data/{k}.laz'))
    L = laspy.read(f); x, y, z = np.asarray(L.x), np.asarray(L.y), np.asarray(L.z)
    m = (x >= bx[0]) & (x <= bx[2]) & (y >= bx[1]) & (y <= bx[3]) & (L.classification != 7)
    return x[m], y[m], z[m]
with ThreadPoolExecutor(8) as ex: R = list(ex.map(bajar, nodos))
x = np.concatenate([r[0] for r in R]); y = np.concatenate([r[1] for r in R]); z = np.concatenate([r[2] for r in R])
np.savez_compressed('dem/spot2014/puntos.npz', x=x, y=y, z=z); print('puntos', len(x), 'densidad', round(len(x) / ((bx[2] - bx[0]) * (bx[3] - bx[1])), 4), 'pts/m²', 'z', z.min(), z.max())
