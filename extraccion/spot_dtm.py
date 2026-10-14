# Terreno desnudo a 4 m desde la nube SPOT 2014 (superficie fotogramétrica): mínimo z por celda de 4 m → relleno de huecos →
# filtro morfológico progresivo (apertura con ventanas crecientes 8–40 m y umbral de pendiente, tipo SMRF simplificado) para retirar
# edificios y copas → suavizado leve. Salida: dem/spot2014/dtm_4m.npy en la grilla de terreno.npz y perfiles de comparación.
import numpy as np, json
from scipy import ndimage as nd
from pyproj import Transformer
T = np.load('terreno.npz'); X0, Y0, DX, NX, NY = float(T['X0']), float(T['Y0']), float(T['DX']), int(T['NX']), int(T['NY'])
P = np.load('dem/spot2014/puntos.npz'); x, y, z = P['x'], P['y'], P['z']
i = ((x - X0) / DX).astype(int); j = ((y - Y0) / DX).astype(int); m = (i >= 0) & (i < NX) & (j >= 0) & (j < NY)
G = np.full((NY, NX), np.inf); np.minimum.at(G, (j[m], i[m]), z[m]); G[np.isinf(G)] = np.nan
vacias = np.isnan(G).mean()
idx = nd.distance_transform_edt(np.isnan(G), return_distances=False, return_indices=True); G = G[tuple(idx)]
S = G.copy()
for w, dz in ((3, 1.0), (5, 1.5), (7, 2.5), (11, 4.0)):            # ventanas de 12–44 m; umbral de altura sobre la apertura
    op = nd.grey_opening(S, size=(w, w)); S = np.where(S - op > dz, op, S)
D = nd.gaussian_filter(S, 1.0)
np.save('dem/spot2014/dtm_4m.npy', D.astype(np.float32))
tf = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True)
def perfil(pts):
    P = np.array([tf.transform(lo, la) for la, lo in pts]); out = []
    for a, b in zip(P[:-1], P[1:]):
        for t in np.linspace(0, 1, int(np.hypot(*(b - a)) / 20) + 1, endpoint=False): out.append(a + (b - a) * t)
    out = np.array(out); ii = ((out[:, 0] - X0) / DX).astype(int); jj = ((out[:, 1] - Y0) / DX).astype(int)
    return np.c_[T['DTM'][jj, ii], D[jj, ii], T['DSM'][jj, ii]]
cauce = [(-33.40030, -70.49960), (-33.40059, -70.50080), (-33.40088, -70.50621), (-33.40181, -70.50988), (-33.40334, -70.51265), (-33.40381, -70.51323), (-33.40586, -70.51609)]
pc = perfil(cauce)
# depresión transversal del cauce: cota en el eje menos promedio a ±40 m perpendicular (negativo = el cauce está más bajo)
def depresion(Z, pts):
    P = np.array([tf.transform(lo, la) for la, lo in pts]); r = []
    for a, b in zip(P[:-1], P[1:]):
        d = (b - a) / np.hypot(*(b - a)); n = np.array([-d[1], d[0]])
        for t in np.linspace(0.1, 0.9, 5):
            c = a + (b - a) * t; s = lambda q: Z[int((q[1] - Y0) / DX), int((q[0] - X0) / DX)]
            r.append(s(c) - 0.5 * (s(c + 40 * n) + s(c - 40 * n)))
    return np.round(np.array(r), 2)
print('celdas sin puntos', round(float(vacias), 3))
print('dif SPOT-DTM − FABDEM en el área: media', round(float(np.nanmean(D - T['DTM'])), 2), 'm, desv', round(float(np.nanstd(D - T['DTM'])), 2), 'm')
print('depresión del cauce (eje − márgenes a 40 m), FABDEM:', depresion(T['DTM'], cauce))
print('depresión del cauce, SPOT filtrado:           ', depresion(D, cauce))
