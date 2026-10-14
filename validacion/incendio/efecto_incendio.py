# Efecto del incendio de dic-2025 en el volumen y la probabilidad del flujo, con la severidad medida (dnbr_resumen.json).
# (1) Balance lluvia–escorrentía del escenario de suelo saturado (volumen_previo.py: P 20–40 mm, f_w 0,6–1) con el coeficiente de
#     escorrentía por clase de severidad: C_u en la parte sin quemar (suelo húmedo tras 95 mm del 5–7 oct) y C_u + Δ_clase en lo quemado
#     (hidrofobicidad y pérdida de cobertura). Sin incendio: C_u en toda la cuenca y una mezcla con menos sólidos (C_v menor).
#     Los Δ y los C_v son SUPUESTOS (rangos uniformes), no mediciones; el resultado es una comparación de escenarios, no una predicción.
# (2) Modelo empírico de volumen para cuencas quemadas (Gartner et al. 2014) con B_mh medido en vez del rango supuesto 0,3–0,9.
# (3) Probabilidad de flujo de detritos, modelo M1 de Staley et al. (2017): logit P = −3,63 + 0,41·T·R + 0,67·F·R + 0,70·S·R, con R la lluvia
#     máxima en 15 min (mm), T la fracción con severidad moderada-alta (sin filtro de pendiente: cota superior), F el dNBR medio y S el
#     factor KF del suelo. Sin incendio, T = F = 0. Calibrado en el oeste de EE. UU.: su uso aquí es ilustrativo.
import json, numpy as np
D = json.load(open('validacion/incendio/dnbr_resumen.json'))['cuencas']; cu = json.load(open('cuenca.json'))
rng = np.random.default_rng(20261012); N = 200000; A = D['total']['area_valida_km2'] * 1e6
k = D['total']['km2_por_clase']; f = {c: k[c] * 1e6 / A for c in k}
P = rng.uniform(0.020, 0.040, N); fw = rng.uniform(0.6, 1.0, N); Cu = rng.uniform(0.40, 0.60, N)
d1, d2, d3 = rng.uniform(0.05, 0.15, N), rng.uniform(0.15, 0.30, N), rng.uniform(0.25, 0.45, N)
Cq = (f['sin quemar'] * Cu + f['baja'] * np.minimum(Cu + d1, .95) + f['moderada-baja'] * np.minimum(Cu + d2, .95)
      + (f['moderada-alta'] + f['alta']) * np.minimum(Cu + d3, .95))
Cv_q = rng.uniform(0.30, 0.50, N); Cv_n = rng.uniform(0.20, 0.35, N)
Vq = fw * P * A * Cq / (1 - Cv_q); Vn = fw * P * A * Cu / (1 - Cv_n); Wq = fw * P * A * Cq; Wn = fw * P * A * Cu
q = lambda v, p=(5, 50, 95): [int(round(float(x), -3)) if abs(x) > 1000 else round(float(x), 3) for x in np.percentile(v, p)]
out = {'C_efectivo_con_incendio': q(Cq), 'C_sin_incendio': q(Cu),
       'agua_con_incendio_m3': q(Wq), 'agua_sin_incendio_m3': q(Wn), 'razon_agua_sin_con': q(Wn / Wq),
       'mezcla_con_incendio_m3': q(Vq), 'mezcla_sin_incendio_m3': q(Vn), 'razon_mezcla_sin_con': q(Vn / Vq),
       'solidos_con_incendio_m3': q(Vq * Cv_q), 'solidos_sin_incendio_m3': q(Vn * Cv_n), 'razon_solidos_sin_con': q(Vn * Cv_n / (Vq * Cv_q))}
# (2) Gartner 2014 con B_mh medido, i15 entre 22 y 44 mm/h (≥ la intensidad de 30 min de Río Molina, 21,8 mm/h)
i15 = rng.uniform(22, 44, N); eps = rng.normal(0, 1.04, N); ndep = rng.uniform(0.25, 0.40, N); Vdep = np.zeros(N)
for c in ('H1', 'S1'):
    Vdep += np.exp(4.22 + 0.39 * np.sqrt(i15) + 0.36 * np.log(D[c]['Bmh_km2']) + 0.13 * np.sqrt(cu[c]['relieve_R_m']) + eps)
out['gartner2014_Bmh_medido'] = {'Bmh_km2': {c: D[c]['Bmh_km2'] for c in ('H1', 'S1', 'S2')}, 'V_deposito_m3': q(Vdep), 'V_mezcla_m3': q((1 - ndep) * Vdep / Cv_q)}
# (3) Staley 2017 M1 (R en mm de lluvia en 15 min: entre la mitad y 3/4 del máximo de 30 min, 10,9 mm)
R = rng.uniform(5.45, 8.2, N); S = rng.uniform(0.15, 0.30, N); T = (D['H1']['Bmh_km2']) / D['H1']['area_valida_km2']; F = D['H1']['dnbr_mediana']
lg = lambda x: 1 / (1 + np.exp(-x))
out['staley2017_M1_cuenca_H1'] = {'T': round(T, 3), 'F_dNBR': F, 'P_con_incendio': q(lg(-3.63 + 0.41 * T * R + 0.67 * F * R + 0.70 * S * R)), 'P_sin_incendio': q(lg(-3.63 + 0.70 * S * R))}
out['nota'] = 'Percentiles 5, 50 y 95. Supuestos: C_u 0,40–0,60; Δ baja 0,05–0,15, mod.-baja 0,15–0,30, mod.-alta/alta 0,25–0,45; C_v con incendio 0,30–0,50 y sin incendio 0,20–0,35.'
json.dump(out, open('validacion/incendio/efecto_incendio.json', 'w'), indent=1, ensure_ascii=False); print(json.dumps(out, indent=1, ensure_ascii=False))
