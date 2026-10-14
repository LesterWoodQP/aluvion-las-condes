# Métricas del sector campus / La Plaza Sur / camino / bike park para microsimulaciones: python evaluar_campus.py id1 id2 ...
import sys, numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree
tf = Transformer.from_crs(4326, 32719, always_xy=True)
src = open('calibrar.py').read(); ns = {}; exec(src[:src.index('PRESENCIA =')], ns)
D = next(v for v in ns.values() if isinstance(v, dict) and any('La Plaza' in k for k in v))
P = {'inicio camino': (-33.40620783, -70.49503026), 'final camino': (-33.4046162, -70.5038762), 'claro': (-33.4032749, -70.5051069), 'patio': (-33.40327, -70.506151), 'estac.': (-33.404866, -70.504556)}
for c in sys.argv[1:]:
    d = np.load(f'res/{c}.npz'); t = cKDTree(np.c_[d['cx'], d['cy']]); out = []
    for n, (la, lo) in P.items():
        x, y = tf.transform(lo, la); r = np.hypot(d['cx'] - x, d['cy'] - y); i = r <= 15
        out.append(f"{n} {d['hmax'][i].max():.2f}" if i.any() else f'{n} —')
    pts = np.asarray(D['La Plaza Sur (Portillo→Clínica U. Andes)']); idx = t.query_ball_point(pts, 12); h = np.array([d['hmax'][i].max() if i else 0 for i in idx])
    print(c, ' · '.join(out), f'· La Plaza Sur >5 cm {np.mean(h > 0.05) * 100:.0f} % máx {h.max():.2f}')
