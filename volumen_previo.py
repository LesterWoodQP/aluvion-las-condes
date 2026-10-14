# Volumen previo de mezcla (v3, revisión A2 §4). Dos estimaciones que NO se concatenan: se reportan por separado y la calibración
# barre un rango que cubre ambas medianas con margen. Cuencas UTM (cuenca.json): H1 + S1 + S2 (aportes que llegan a la urbanización).
#
# (1) Balance lluvia–escorrentía con agua y sólidos diferenciados:
#       V_w = f_w · P · A · C           (f_w: fracción de la escorrentía que se incorpora al pulso; el resto se queda en ductos/cauce)
#       V_s = V_w · Cv/(1 − Cv)          V_m = V_w + V_s = V_w/(1 − Cv)
#     P ∈ [12, 35] mm (pulso; Tobalaba 13,8 mm en 15–21 h y ~16–20 mm/h en prensa, con factor orográfico ≤ 1,8 hacia la cuenca alta)
#     C ∈ [0,3; 0,8]  (suelo húmedo tras 49 mm el 6–7 oct y ladera quemada; no se asume saturación completa — A2)
#     f_w ∈ [0,5; 1,0]; Cv_total ∈ [0,30; 0,50]
# (2) Gartner, Cannon & Santi (2014): ln V_dep = 4,22 + 0,39 √i15 + 0,36 ln B_mh + 0,13 √R + ε,  ε ~ N(0; 1,04²)
#     V_dep es volumen de DEPÓSITO de sedimento; se convierte a mezcla: V_m = (1 − n_dep) V_dep / Cv_total, n_dep ∈ [0,25; 0,40].
#     B_mh = fracción quemada de severidad moderada–alta de cada cuenca × área, fracción ∈ [0,3; 0,9] (perímetro y severidad del incendio
#     de dic-2025 no publicados; Parque San Carlos de Apoquindo, 1.012 ha). i15 ∈ [25, 60] mm/h. Modelo calibrado en el sur de California:
#     su aplicabilidad aquí es una hipótesis (A2).
import json, numpy as np
rng = np.random.default_rng(20261008); N = 400000
cu = json.load(open('cuenca.json')); ap = ('H1', 'S1', 'S2')
A = sum(cu[k]['area_km2'] for k in ap) * 1e6
P = rng.uniform(0.012, 0.035, N); C = rng.uniform(0.3, 0.8, N); fw = rng.uniform(0.5, 1.0, N); Cv = rng.uniform(0.30, 0.50, N)
Vw = fw * P * A * C; Vm1 = Vw / (1 - Cv)
i15 = rng.uniform(25, 60, N); fq = rng.uniform(0.3, 0.9, N); ndep = rng.uniform(0.25, 0.40, N); eps = rng.normal(0, 1.04, N)
Vdep = np.zeros(N)
for k in ap:   # Gartner por subcuenca (el modelo es por cuenca) y se suma
    Vdep += np.exp(4.22 + 0.39 * np.sqrt(i15) + 0.36 * np.log(fq * cu[k]['area_km2']) + 0.13 * np.sqrt(cu[k]['relieve_R_m']) + eps)
Vm2 = (1 - ndep) * Vdep / Cv
Vm2_sin_eps = None
q = lambda v: {f'p{p}': int(round(float(np.percentile(v, p)), -2)) for p in (5, 25, 50, 75, 95)}
fr = {k: round(cu[k]['area_km2'] * 1e6 / A, 3) for k in ap}
out = {'area_aportante_km2': round(A / 1e6, 3), 'fraccion_por_area': fr,
       'balance_lluvia_escorrentia': {'V_agua_m3': q(Vw), 'V_mezcla_m3': q(Vm1)},
       'gartner2014_con_residuo': {'V_deposito_m3': q(Vdep), 'V_mezcla_m3': q(Vm2)},
       'nota': 'Distribuciones inducidas por supuestos uniformes documentados; no son intervalos medidos. No se combinan en una sola previa.'}
for V in (float(np.percentile(Vm1, 50)),):
    out['Qp_mizuyama1992_flujo_barro_m3s_para_mediana_balance'] = round(0.0188 * V ** 0.79, 0)
# Escenario con suelo saturado (evidencia 10-oct: ~150 mm en la cuenca entre el 2 y el 8 de octubre según el pronóstico histórico de
# Open-Meteo; isoterma 0 °C a 2.540–3.000 m el 8-oct → lluvia en toda la cuenca; sin manto nival previo por Sentinel-2 NDSI):
# P del pulso ∈ [20, 40] mm (convectivo, sobre los ~15 mm suavizados del modelo y los 16–20 mm/h de prensa), C ∈ [0,6; 0,9], f_w ∈ [0,6; 1]
P2 = rng.uniform(0.020, 0.040, N); C2 = rng.uniform(0.6, 0.9, N); fw2 = rng.uniform(0.6, 1.0, N)
Vm3 = fw2 * P2 * A * C2 / (1 - Cv)
out['balance_suelo_saturado'] = {'V_agua_m3': q(fw2 * P2 * A * C2), 'V_mezcla_m3': q(Vm3)}
out['deshielo_cota_superior_m3'] = int(0.31e6 * 0.05)   # 0,31 km² sobre 2.000 m × 50 mm de equivalente en agua (no había manto previo)
out['rango_para_calibrar_m3'] = [int(round(float(min(np.percentile(Vm1, 10), np.percentile(Vm2, 25))), -3)), int(round(float(max(np.percentile(Vm1, 90), np.percentile(Vm2, 75))), -3))]
json.dump(out, open('res/volumen_previo.json', 'w'), indent=1, ensure_ascii=False); print(json.dumps(out, indent=1, ensure_ascii=False))
