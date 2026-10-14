# Exposición y pérdida relativa esperada (sub-estudio censal, v3; correcciones de la revisión E1).
# Cambios respecto de v2:
#  (1) Unidades censales disueltas por MANZENT_I (las agrupaciones «901» vienen como varias geometrías con el mismo total; el total se
#      cuenta una sola vez) y re-consulta de esas unidades completas al servicio del INE.
#  (2) Ponderación areal exacta sobre una retícula de 4 m: f_j = |{celdas de M_j con h>h*}| / |{celdas de M_j}|, con h interpolado
#      linealmente desde los centroides de la malla; se informa la fracción de cada unidad cubierta por el dominio.
#  (3) Exposición del edificio por distancia real a su huella: máximo de h en las celdas a ≤ r de la huella (r = 4, 8, 16 m).
#  (4) Dasimetría con pesos por área de intersección huella–unidad censal (huellas 30–2.000 m²); unidades sin huellas elegibles se
#      asignan por ponderación areal (alternativa explícita) y se informan aparte.
#  (5) Curvas: Fuchs et al. (2007) solo en su dominio (0 ≤ h < 2,5 m; recorte a 0 bajo ~0,18 m); los edificios con h ≥ 2,5 m se
#      cuentan aparte («fuera del dominio de Fuchs»). Papathoma-Köhle et al. (2012) sin recorte. ΣV se informa como pérdida
#      relativa agregada (no como edificios destruidos).
#  (6) Longitud de calles con barro (OSM, por tramo) calculada aquí para que sea reproducible.
# Uso: python exposicion3.py res/v01.npz ...   → res/exposicion3.json
import sys, json, numpy as np, shapely, urllib.request, urllib.parse
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely.strtree import STRtree
from pyproj import Transformer
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, cKDTree
tf = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True)
to_utm = lambda g: shapely.transform(g, lambda c: np.c_[tf.transform(c[:, 0], c[:, 1])])
DX = 4.0
# ---------- (1) unidades censales disueltas
F = json.load(open('dem/censo/manzanas.geojson'))['features']
grupos = {}
for f in F: grupos.setdefault(f['properties']['MANZENT_I'], []).append(f)
URL = 'https://services9.arcgis.com/kKJR3Qt68ohAWuet/arcgis/rest/services/Manzanas_censo_2017/FeatureServer/0/query'
rep = [k for k, v in grupos.items() if len(v) > 1 or str(k).endswith('901')]
CACHE = 'dem/censo/unidades_completas.json'   # caché: la consulta al servicio se hace una vez y queda en el registro probatorio
import os
if os.path.exists(CACHE): grupos.update({int(k) if str(k).isdigit() else k: v for k, v in json.load(open(CACHE)).items()})
else:
    for k in rep:   # recupera todas las partes de la unidad, aunque caigan fuera del rectángulo de descarga
        q = {'where': f"MANZENT_I={k}", 'outFields': 'MANZENT_I,NOM_COMUNA,TOTAL_PERS,TOTAL_VIVI', 'returnGeometry': 'true', 'outSR': 4326, 'f': 'geojson'}
        try: grupos[k] = json.loads(urllib.request.urlopen(URL + '?' + urllib.parse.urlencode(q), timeout=60).read())['features'] or grupos[k]
        except Exception: pass
    json.dump({str(k): grupos[k] for k in rep}, open(CACHE, 'w'))
    sys.path.insert(0, 'fuentes'); from registrar import registrar
    registrar('archivo', CACHE, f'INE Censo 2017 (ArcGIS Manzanas_censo_2017): partes completas de {len(rep)} unidades censales agrupadas («901» o con varias geometrías), consultadas por MANZENT_I', CACHE)
U = []
for k, fs in grupos.items():
    vv = {(f['properties']['TOTAL_VIVI'], f['properties']['TOTAL_PERS']) for f in fs}
    assert len(vv) == 1, f'atributos distintos en {k}'
    V, P = vv.pop(); g = to_utm(unary_union([shape(f['geometry']) for f in fs]).buffer(0))
    U.append({'id': k, 'comuna': fs[0]['properties']['NOM_COMUNA'], 'V': V or 0, 'P': P or 0, 'g': g, 'partes': len(fs)})
UG = [u['g'] for u in U]; tree_u = STRtree(UG)
print(f'unidades censales: {len(U)} (de {len(F)} registros) · viviendas {sum(u["V"] for u in U)} · personas {sum(u["P"] for u in U)} · unidades multiparte {sum(u["partes"] > 1 for u in U)}')
# ---------- huellas
B = [to_utm(shape(g['geometry'])).buffer(0) for g in json.load(open('dem/overture/edificios.geojson'))['features']]
area = np.array([b.area for b in B]); elig = (area >= 30) & (area <= 2000)
# pesos dasimétricos por intersección huella–unidad
peso = {}   # (b, j) -> área de intersección
tree_b = STRtree(B)
for j, g in enumerate(UG):
    for b in tree_b.query(g, predicate='intersects'):
        if elig[b]:
            a = B[b].intersection(g).area
            if a > 1: peso[(b, j)] = a
tot = np.zeros(len(U)); [tot.__setitem__(j, tot[j] + a) for (b, j), a in peso.items()]
sin_huellas = [j for j in range(len(U)) if tot[j] == 0 and U[j]['V'] > 0]
viv_b = np.zeros(len(B)); per_b = np.zeros(len(B))
for (b, j), a in peso.items(): viv_b[b] += U[j]['V'] * a / tot[j]; per_b[b] += U[j]['P'] * a / tot[j]
print(f'unidades con viviendas sin huellas elegibles: {len(sin_huellas)} ({sum(U[j]["V"] for j in sin_huellas)} viviendas) · pares huella–unidad {len(peso)}')
FU = lambda h: np.where(h < 2.5, np.clip(0.11 * h ** 2 - 0.02 * h, 0, 1), np.nan)
PK = lambda h: 1 - np.exp(-0.270 * (np.maximum(h, 0) / 1.287) ** 2.974)
o_calles = json.load(open('osm.json'))['calles']
def calcular(f):
    r = np.load(f); xy = np.c_[r['cx'], r['cy']]; h = r['hmax'].astype(float)
    x0, x1, y0, y1 = xy[:, 0].min(), xy[:, 0].max(), xy[:, 1].min(), xy[:, 1].max()
    gx = np.arange(x0 + DX / 2, x1, DX); gy = np.arange(y0 + DX / 2, y1, DX); GX, GY = np.meshgrid(gx, gy)
    H = LinearNDInterpolator(Delaunay(xy), h)(GX, GY)            # NaN fuera de la envolvente de la malla
    dom = np.isfinite(H); H = np.nan_to_num(H)
    def celdas(g):
        bx0, by0, bx1, by1 = g.bounds
        i0, i1 = max(0, int((bx0 - x0) / DX)), min(len(gx), int((bx1 - x0) / DX) + 2); j0, j1 = max(0, int((by0 - y0) / DX)), min(len(gy), int((by1 - y0) / DX) + 2)
        if i1 <= i0 or j1 <= j0: return None
        sx, sy = GX[j0:j1, i0:i1], GY[j0:j1, i0:i1]; m = shapely.contains_xy(g, sx, sy)
        return H[j0:j1, i0:i1][m], dom[j0:j1, i0:i1][m]
    out = {'corrida': f.split('/')[-1][:-4], 'params': {k: v for k, v in json.loads(str(r['params'])).items() if k in ('origen', 'vol', 'qp', 'terreno', 'colector', 'lluvia', 'cfl', 'suelo')}, 'sens': {}}
    # (2) ponderación areal exacta
    UMB = (0.02, 0.05, 0.10, 0.30, 0.50, 1.00); viv_a = {u: 0.0 for u in UMB}; per_a = {u: 0.0 for u in UMB}; parcial = 0; fr05 = np.zeros(len(U))
    for j, u_ in enumerate(U):
        c = celdas(u_['g'])
        if c is None or not len(c[0]): continue
        hv, dv = c; cub = dv.mean()
        if cub < 0.999: parcial += 1
        for u in UMB:
            fj = float((hv > u).mean()); viv_a[u] += fj * u_['V']; per_a[u] += fj * u_['P']
            if u == 0.05: fr05[j] = fj
    # (3) exposición por distancia real a la huella
    cen = np.array([[b.centroid.x, b.centroid.y] for b in B])
    dentro = (cen[:, 0] > x0) & (cen[:, 0] < x1) & (cen[:, 1] > y0) & (cen[:, 1] < y1)
    hb = {}
    for rr in (4.0, 8.0, 16.0):
        hv = np.zeros(len(B))
        for i in np.nonzero(dentro)[0]:
            c = celdas(B[i].buffer(rr)); hv[i] = c[0].max() if c is not None and len(c[0]) else 0.0
        hb[rr] = hv
    for u in (0.02, 0.05, 0.10, 0.30):
        for rr in (4.0, 8.0, 16.0):
            e = dentro & (hb[rr] > u)
            vd = float(viv_b[e].sum()) + sum(U[j]['V'] * ((celdas(U[j]['g'])[0] > u).mean() if celdas(U[j]['g']) is not None and len(celdas(U[j]['g'])[0]) else 0) for j in sin_huellas)
            pd = float(per_b[e].sum()) + sum(U[j]['P'] * ((celdas(U[j]['g'])[0] > u).mean() if celdas(U[j]['g']) is not None and len(celdas(U[j]['g'])[0]) else 0) for j in sin_huellas)
            out['sens'][f'h{u}_r{int(rr)}'] = {'edificios': int(e.sum()), 'viv_dasim': round(vd), 'per_dasim': round(pd), 'viv_areal': round(viv_a[u]), 'per_areal': round(per_a[u])}
    h8 = np.where(dentro, hb[8.0], 0.0); fu, pk = FU(h8), PK(h8)
    out['edif_h'] = {f'>{u}': int((h8 > u).sum()) for u in (0.05, 0.3, 0.5, 1.0, 2.5)}
    out['viv_areal_h'] = {f'>{u}': round(viv_a[u]) for u in UMB}
    out['danio'] = {'fuchs_suma_V': round(float(np.nansum(fu)), 1), 'pk_suma_V': round(float(pk.sum()), 1), 'fuera_dominio_fuchs_h>=2.5': int((h8 >= 2.5).sum()),
                    'fuchs_edif_V>=0.2': int(np.nansum(fu >= 0.2)), 'pk_edif_V>=0.2': int((pk >= 0.2).sum()), 'pk_edif_V>=0.5': int((pk >= 0.5).sum()),
                    'fuchs_viv_V>=0.2': round(float(viv_b[(fu >= 0.2) & np.isfinite(fu)].sum())), 'pk_viv_V>=0.2': round(float(viv_b[pk >= 0.2].sum())),
                    'pk_viv_V>=0.5': round(float(viv_b[pk >= 0.5].sum())), 'viv_h>=2.5': round(float(viv_b[h8 >= 2.5].sum()))}
    for rr in (4.0, 16.0):   # sensibilidad del daño al radio
        p2 = PK(np.where(dentro, hb[rr], 0)); out['danio'][f'pk_viv_V>=0.2_r{int(rr)}'] = round(float(viv_b[p2 >= 0.2].sum()))
    out['unidades_parcialmente_en_dominio'] = parcial; out['hist_h_edificios'] = np.histogram(h8[h8 > 0.05], bins=[0.05, 0.1, 0.3, 0.5, 1, 1.5, 2, 3, 10])[0].tolist()
    # (6) calles con barro
    t = cKDTree(xy); L = {'todas': 0.0, 'primarias_terciarias': 0.0}
    for c in o_calles:
        Pp = np.array([tf.transform(b, a) for a, b in c['pts']])
        for a_, b_ in zip(Pp[:-1], Pp[1:]):
            d, i = t.query((a_ + b_) / 2)
            if d <= 12 and h[i] > 0.05:
                s = float(np.hypot(*(b_ - a_))); L['todas'] += s
                if c['k'] in ('primary', 'secondary', 'tertiary'): L['primarias_terciarias'] += s
    out['km_calles_con_barro'] = {k: round(v / 1000, 1) for k, v in L.items()}
    feats = [{'type': 'Feature', 'properties': {'id': U[j]['id'], 'viviendas': U[j]['V'], 'frac_05': round(fr05[j], 3), 'viv_expuestas': round(fr05[j] * U[j]['V'], 1)},
              'geometry': mapping(shapely.transform(U[j]['g'], lambda cc: np.c_[Transformer.from_crs('EPSG:32719', 'EPSG:4326', always_xy=True).transform(cc[:, 0], cc[:, 1])]))} for j in range(len(U)) if fr05[j] > 0]
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(f'res/exposicion3_{out["corrida"]}.geojson', 'w'))
    print(out['corrida'], out['sens']['h0.05_r8'], out['danio'], out['km_calles_con_barro'], flush=True)
    return out
res = {'unidades_censales': len(U), 'registros': len(F), 'viviendas_universo': int(sum(u['V'] for u in U)), 'personas_universo': int(sum(u['P'] for u in U)),
       'unidades_sin_huellas': len(sin_huellas), 'viv_sin_huellas': int(sum(U[j]['V'] for j in sin_huellas)), 'res': [calcular(f) for f in sys.argv[1:]]}
json.dump(res, open('res/exposicion3.json', 'w'), indent=1, ensure_ascii=False)
