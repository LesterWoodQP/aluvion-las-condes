# Tapón de troncos y detritos en el extremo oeste de la línea de árboles (KML de Lester, 11-oct-2026): eleva el terreno dentro del
# polígono en una altura supuesta (por defecto 3 m). Representante grueso de una obstrucción, no una medición. Uso: python terreno_tapon.py BASE SALIDA [ALTURA]
import sys, json, numpy as np
from pyproj import Transformer
from matplotlib.path import Path
B, S = sys.argv[1], sys.argv[2]; H = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
T = dict(np.load(B)); DX = float(T['DX']); gx = T['X0'] + (np.arange(int(T['NX'])) + .5) * DX; gy = T['Y0'] + (np.arange(int(T['NY'])) + .5) * DX
tf = Transformer.from_crs(4326, 32719, always_xy=True); poly = [tf.transform(lo, la) for la, lo in json.load(open('poligono_tapon_arboles.json'))]
X, Y = np.meshgrid(gx, gy); m = Path(poly).contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(X.shape)
T['ELEV'] = T['ELEV'] + H * m; np.savez_compressed(S, **T); print(f'tapón: {int(m.sum())} celdas ({m.sum() * DX * DX:.0f} m²) elevadas {H} m → {S}')
