# Métricas de coincidencia entre una corrida y las observaciones cualitativas del evento (ver fuentes/FUENTES.md).
# Observaciones (todas de prensa/municipio, sin cartografía oficial):
#   O1 polígono municipal: N Camino El Alba · E Av. La Plaza · S Quebrada Honda · W Av. Padre Hurtado
#   O2 calles cerradas por barro: Av. La Plaza (Portillo→El Alba), Mons. Álvaro del Portillo (La Plaza→San Carlos de Apoquindo),
#      Av. San Carlos de Apoquindo (Portillo→El Alba), General Blanche (San Carlos de Apoquindo→Las Condesas), Quebrada Honda,
#      Camino El Alba ("bajó por" El Alba, General Blanche y Quebrada Honda)
#   O3 alcance: llegó hasta el sector Pueblito Los Dominicos / Av. Padre Hurtado
# Métricas:
#   R (sensibilidad) = fracción de puntos de control O2 con h_max > 5 cm (vecino más cercano ≤ 12 m)
#   P (precisión)    = fracción del área con h_max > 5 cm que cae dentro de O1 ampliado 100 m
#   A (alcance)      = 1 si hay celda con h_max > 5 cm a ≤ 200 m del cruce General Blanche × Padre Hurtado, si no 0
#   F = 2PR/(P+R) · (0,5 + 0,5 A)
# v3 (revisión A2 §5): las calles cerradas quedan como contexto (no puntúan); se agregan observaciones puntuales de sitios con
# presencia confirmada por varias fuentes; los criterios de aceptación se fijan ANTES de ver los resultados (estilo GLUE):
#   R_lineal ≥ 0,6 en calles con presencia confirmada · S_sitios ≥ 3/4 · alcance a Padre Hurtado · P ≥ 0,5
#   peso informal L = R_lineal · S_sitios · P (solo para corridas aceptables)
# Uso: python calibrar.py res/run_*.npz   (agrega una fila por corrida a res/corridas.csv)
import sys, json, csv, os, numpy as np
from scipy.spatial import cKDTree
from pyproj import Transformer
from matplotlib.path import Path

tf = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True)
U = lambda lat, lon: tf.transform(lon, lat)
o = json.load(open('osm.json'))
def calle(nombre, lat=(-90, 90), lon=(-180, 180), k=None):
    pts = []
    for c in o['calles']:
        if c['name'] != nombre or (k and c['k'] not in k): continue
        for a, b in c['pts']:
            if lat[0] <= a <= lat[1] and lon[0] <= b <= lon[1]: pts.append(U(a, b))
    return pts
def densificar(pts, paso=10.0):
    if len(pts) < 2: return pts
    pts = sorted(pts); out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d = np.hypot(x1 - x0, y1 - y0); n = max(1, int(d / paso))
        if d > 150: continue                     # salto entre tramos distintos
        out += [(x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * t / n) for t in range(n)]
    return out + [pts[-1]]
CONTROL = {
    'La Plaza (Portillo→El Alba)': densificar(calle('Avenida La Plaza', lat=(-33.4014, -33.3994), lon=(-70.5070, -70.5060))),
    'Álvaro del Portillo': densificar(calle('Avenida Monseñor Álvaro del Portillo', lon=(-70.5102, -70.5062), k=('secondary',))),
    'San Carlos de Apoquindo (Portillo→El Alba)': densificar(calle('Avenida San Carlos de Apoquindo', lat=(-33.4017, -33.3995), lon=(-70.512, -70.508))),
    'General Blanche (SCA→Las Condesas)': densificar(calle('General Blanche', lon=(-70.5245, -70.5099))),
    'Quebrada Honda': densificar(calle('Quebrada Honda')),
    'Camino El Alba': densificar(calle('Camino El Alba', lon=(-70.545, -70.5065))),
    'La Plaza Sur (Portillo→Clínica U. Andes)': densificar(calle('Avenida La Plaza', lat=(-33.4085, -33.4016), lon=(-70.5066, -70.5020))),
    # agregada el 9-oct tras el cribado (Senapred vía El Dínamo): se informa como presencia, pero no entra en R_presencia (criterio fijado antes)
    'Vital Apoquindo (Senapred, post hoc)': densificar(calle('Vital Apoquindo', lat=(-33.4200, -33.4060))),
}
# sitios con presencia confirmada (radio de tolerancia 40 m alrededor del punto geocodificado; fuentes/registro_consultas.jsonl)
SITIOS = {'Clínica UC Christus SCA (~1 m en urgencias)': U(-33.40014, -70.50874), 'Clínica U. de los Andes (exterior y accesos)': U(-33.40727, -70.50373),
          'Duoc UC San Carlos de Apoquindo': U(-33.40063, -70.50540), 'Campus U. de los Andes (Portillo)': U(-33.40424, -70.50660)}
alba = sorted(calle('Camino El Alba', lon=(-70.5452, -70.5065)), key=lambda p: -p[0])
qh = sorted(calle('Quebrada Honda'), key=lambda p: p[0])
from shapely.geometry import Polygon
from shapely.validation import make_valid
_pg = make_valid(Polygon(alba + [U(-33.4079, -70.5451), U(-33.4125, -70.5405)] + qh + [U(-33.4052, -70.5024), U(-33.3995, -70.5067)]))
_pg = max(getattr(_pg, 'geoms', [_pg]), key=lambda g: g.area) if _pg.geom_type != 'Polygon' else _pg
POLY = list(_pg.exterior.coords)[:-1]   # perímetro municipal sin autointersecciones (A2 §5)
PH = np.array(U(-33.40918, -70.54224))

def buffer_mask(xy, poly, d):
    path = Path(poly); inside = path.contains_points(xy)
    if d <= 0: return inside
    P = np.array(poly); segs = np.c_[P, np.roll(P, -1, axis=0)]
    dmin = np.full(len(xy), np.inf)
    for x0, y0, x1, y1 in segs:
        vx, vy = x1 - x0, y1 - y0; L2 = vx * vx + vy * vy or 1.0
        t = np.clip(((xy[:, 0] - x0) * vx + (xy[:, 1] - y0) * vy) / L2, 0, 1)
        dmin = np.minimum(dmin, np.hypot(xy[:, 0] - x0 - t * vx, xy[:, 1] - y0 - t * vy))
    return inside | (dmin <= d)

# A1 §7: separar presencia confirmada (prensa: "bajó por", autos arrastrados) de cierres (pueden ser preventivos)
PRESENCIA = ['Camino El Alba', 'General Blanche (SCA→Las Condesas)', 'Quebrada Honda', 'La Plaza (Portillo→El Alba)', 'La Plaza Sur (Portillo→Clínica U. Andes)']
CIERRE = ['Álvaro del Portillo', 'San Carlos de Apoquindo (Portillo→El Alba)']
def evaluar(f, hstar=0.05):
    r = np.load(f); xy = np.c_[r['cx'], r['cy']]; wet = r['hmax'] > hstar; A = r['area']
    tree = cKDTree(xy); res = {}
    hits = tot = 0; hp = tp = 0
    for k, pts in CONTROL.items():
        if not pts: continue
        d, i = tree.query(np.array(pts)); ok = (d <= 12) & wet[i]
        res['R_' + k] = round(float(ok.mean()), 3); hits += ok.sum(); tot += len(pts)
        if k in PRESENCIA: hp += ok.sum(); tp += len(pts)
    R = hits / max(1, tot); Rp = hp / max(1, tp)
    sit = {}
    for k, (x, y) in SITIOS.items():
        ii = tree.query_ball_point([x, y], 40.0); hm = float(r['hmax'][ii].max()) if ii else 0.0
        sit[k] = hm; res['h_' + k.split(' (')[0]] = round(hm, 2)
    S = float(np.mean([v > hstar for v in sit.values()]))
    inpoly = buffer_mask(xy[wet], POLY, 100.0)
    P = float(np.sum(A[wet][inpoly]) / max(1e-9, np.sum(A[wet])))
    # Jaccard contra el perímetro municipal (cota inferior: el perímetro es operativo y puede incluir zonas secas)
    inB = buffer_mask(xy, POLY, 0.0); inter = np.sum(A[wet & inB]); union = np.sum(A[wet | inB])
    J = float(inter / max(1e-9, union))   # descriptivo: el perímetro es operativo, no una huella cartografiada
    dph = np.hypot(xy[wet, 0] - PH[0], xy[wet, 1] - PH[1]).min() if wet.any() else 1e9
    Aok = 1.0 if dph <= 200 else 0.0
    F = (2 * P * R / (P + R) if P + R > 0 else 0) * (0.5 + 0.5 * Aok)   # métrica v2, se conserva solo como referencia
    acept = bool(Rp >= 0.6 and S >= 0.75 and Aok == 1.0 and P >= 0.5)
    L = Rp * S * P if acept else 0.0
    p = json.loads(str(r['params']))
    fila = {'corrida': os.path.basename(f), 'Qp': p['qp'], 'V': p['vol'], 'Cv': p['cv'], 'suelo': p['suelo'], 'Kc': p.get('Kc'), 'nc': p.get('nc'), 'Ko': p.get('Ko'), 'no': p.get('no'), 'cvt': p.get('cvt'),
            'tau_y': round(p['tau_y'], 2), 'eta': round(p['eta'], 3), 'rho_m': round(p['rho_m']),
            'origen': p.get('origen', 'H1'), 'hstar': hstar, 'area_ha': round(float(np.sum(A[wet])) / 1e4, 2), 'R': round(R, 3), 'R_presencia': round(Rp, 3), 'S_sitios': round(S, 2), 'aceptable': acept, 'L': round(L, 4),
            'P': round(P, 3), 'J_perimetro': round(J, 3), 'dist_PH_m': round(float(dph)), 'A': Aok, 'F': round(F, 3),
            'h_max': round(float(r['hmax'].max()), 2), 'V_max': round(float(r['vmax'].max()), 2)} | res
    return fila

if __name__ == '__main__':
    filas = [evaluar(f, hs) for f in sys.argv[1:] for hs in (0.02, 0.05, 0.10)]
    out = 'res/corridas.csv'; nuevo = not os.path.exists(out)
    campos = list(filas[0].keys())
    with open(out, 'a', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction='ignore')
        if nuevo: w.writeheader()
        for fl in filas: w.writerow(fl)
    for fl in filas:
        if fl['hstar'] == 0.05: print({k: fl[k] for k in ('corrida', 'origen', 'Qp', 'V', 'Cv', 'suelo', 'area_ha', 'R_presencia', 'S_sitios', 'P', 'J_perimetro', 'dist_PH_m', 'aceptable', 'L')})
    print('puntos de control:', {k: len(v) for k, v in CONTROL.items()})
