# Cuadratura de Gauss de Cv (validacion/cuadratura_cv.json: Cv = 0,20 + 0,30 X, X ~ Beta(3,2), 5 nodos q1..q5 sobre la configuración v28).
# Valores ESPERADOS y desviación de hmax, vmax y presión dinámica por celda, condicionados a esa distribución de creencia (no son
# probabilidades de inundación: el mojado/secado es discontinuo y la cuadratura no sirve para percentiles ni excedencias).
# Para excedencias se informa, como alternativa explícita, la Cv umbral por celda: la menor Cv nodal con la que la celda supera 5 cm
# (interpolación entre nodos solo como orden de magnitud). Escribe validacion/cuadratura_cv_resultados.json y figura.
import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
Q = json.load(open('validacion/cuadratura_cv.json')); ids = ['q1', 'q2', 'q3', 'q4', 'q5']; w = np.array(Q['pesos']); cv = np.array(Q['Cv'])
D = [np.load(f'res/{i}.npz') for i in ids]
for d in D[1:]: assert len(d['cx']) == len(D[0]['cx']), 'mallas distintas'
A = D[0]['area']; out = {'pesos': w.tolist(), 'Cv': cv.tolist()}
for k in ('hmax', 'vmax', 'pdin'):
    X = np.stack([d[k] for d in D]); m1 = (w[:, None] * X).sum(0); m2 = (w[:, None] * X ** 2).sum(0); sd = np.sqrt(np.maximum(m2 - m1 ** 2, 0))
    wet = m1 > 0.05 if k == 'hmax' else D[0]['hmax'] > -1
    out[k] = {'media_area_mojada': float((m1 * A)[wet].sum() / A[wet].sum()), 'sd_media_area_mojada': float((sd * A)[wet].sum() / A[wet].sum())}
    if k == 'hmax': E_h, SD_h = m1, sd
moj = np.stack([d['hmax'] > 0.05 for d in D])
out['area_h5cm_por_nodo_ha'] = [round(float(A[m].sum() / 1e4), 1) for m in moj]
out['area_h5cm_esperada_ha'] = round(float((w * np.array(out['area_h5cm_por_nodo_ha'])).sum()), 1)
out['area_mojada_en_todos_los_nodos_ha'] = round(float(A[moj.all(0)].sum() / 1e4), 1)
out['area_mojada_en_algun_nodo_ha'] = round(float(A[moj.any(0)].sum() / 1e4), 1)
# Cv umbral: mayor Cv nodal con la que la celda todavía supera 5 cm (más Cv = barro más espeso que llega menos lejos)
cvu = np.full(len(A), np.nan)
for j in range(len(ids)): cvu = np.where(moj[j], cv[j], cvu)
out['area_ha_por_cv_umbral'] = {f'{c:.3f}': round(float(A[cvu == c].sum() / 1e4), 1) for c in cv}   # área que se moja hasta esa Cv y no con las mayores
out['nota'] = 'Valores esperados condicionados a la distribución Beta(3,2) de creencia; no son probabilidades de inundación.'
json.dump(out, open('validacion/cuadratura_cv_resultados.json', 'w'), indent=1)
fig, ax = plt.subplots(1, 2, figsize=(10, 4.2), sharex=True, sharey=True)
cx, cy = D[0]['cx'], D[0]['cy']; s = E_h > 0.05
for a, v, t, cm in ((ax[0], E_h, 'Espesor máximo esperado E[h] (m)', 'viridis'), (ax[1], SD_h, 'Desviación entre nodos σ[h] (m)', 'magma')):
    sc = a.scatter(cx[s], cy[s], c=v[s], s=0.3, cmap=cm, vmax=np.percentile(v[s], 98)); a.set_title(t, fontsize=9); a.set_aspect('equal'); a.set_xticks([]); a.set_yticks([]); fig.colorbar(sc, ax=a, shrink=0.8)
fig.suptitle('Cuadratura de Cv (Beta(3,2), 5 nodos): valores condicionados a la distribución de creencia', fontsize=9)
fig.tight_layout(); fig.savefig('validacion/cuadratura_cv.png', dpi=130)
print(json.dumps({k: out[k] for k in ('area_h5cm_por_nodo_ha', 'area_h5cm_esperada_ha', 'area_mojada_en_todos_los_nodos_ha', 'area_mojada_en_algun_nodo_ha')}, ensure_ascii=False), out['hmax'])
