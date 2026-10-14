# Prueba de control (revisión N1): talla en el terreno el cauce abierto del parque lineal, desde la salida de la quebrada al abanico
# hasta la embocadura del colector en Fco. Bulnes Correa (trazado OSM), que el DEM de 30 m no resuelve.
# Sección rectangular de 8 m de ancho; el fondo desciende monótonamente aguas abajo (mínimo acumulado) y queda 2 m bajo el terreno.
# Salida: terreno_tallado.npz (misma estructura que terreno.npz).
import numpy as np
from pyproj import Transformer
tf = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True)
import sys
ENT = sys.argv[1] if len(sys.argv) > 1 else 'terreno.npz'; SAL = sys.argv[2] if len(sys.argv) > 2 else 'terreno_tallado.npz'
ANCHO = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0; PROF = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0   # sección rectangular (m)
T = dict(np.load(ENT)); X0, Y0, DX, NX, NY = float(T['X0']), float(T['Y0']), float(T['DX']), int(T['NX']), int(T['NY'])
TRAZO = [(-33.40030, -70.49960), (-33.40059, -70.50080), (-33.40088, -70.50621), (-33.40181, -70.50988), (-33.40334, -70.51265),
         (-33.40381, -70.51323), (-33.40586, -70.51609)]
if len(sys.argv) > 5:   # trazado alternativo [[lat, lon], …] de aguas arriba a aguas abajo (p. ej. quebrada Álvaro del Portillo)
    import json; TRAZO = [tuple(q) for q in json.load(open(sys.argv[5]))]
P = np.array([tf.transform(lo, la) for la, lo in TRAZO])
pts = []
for a, b in zip(P[:-1], P[1:]):
    n = int(np.hypot(*(b - a)) / 2) + 1; pts += [a + (b - a) * t for t in np.linspace(0, 1, n, endpoint=False)]
pts.append(P[-1]); pts = np.array(pts)
ii = ((pts[:, 0] - X0) / DX).astype(int); jj = ((pts[:, 1] - Y0) / DX).astype(int)
ELEV, DTM = T['ELEV'].copy(), T['DTM']
z = np.array([DTM[j, i] for i, j in zip(ii, jj)]) - PROF
fondo = np.minimum.accumulate(z)                                   # nunca sube aguas abajo
gx = X0 + (np.arange(NX) + 0.5) * DX; gy = Y0 + (np.arange(NY) + 0.5) * DX
for (x, y), zf in zip(pts, fondo):
    R_ = ANCHO / 2 + 2; i0, i1 = max(0, int((x - R_ - X0) / DX)), min(NX, int((x + R_ - X0) / DX) + 1); j0, j1 = max(0, int((y - R_ - Y0) / DX)), min(NY, int((y + R_ - Y0) / DX) + 1)
    X, Y = np.meshgrid(gx[i0:i1], gy[j0:j1]); m = np.hypot(X - x, Y - y) <= ANCHO / 2
    sub = ELEV[j0:j1, i0:i1]; sub[m] = np.minimum(sub[m], zf)
T['ELEV'] = ELEV.astype(np.float32); np.savez_compressed(SAL, **T)
print(f'cauce tallado: {len(pts)} puntos, {np.hypot(*np.diff(P, axis=0).T).sum():.0f} m, fondo {fondo[0]:.1f} → {fondo[-1]:.1f} m, celdas bajadas {(T["ELEV"] < np.load(ENT)["ELEV"] - 0.01).sum()}')
