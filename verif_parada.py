# Verificación v3 de la resistencia de fluencia (revisión A2 §2–§3). Plano inclinado S, canal de 20 m, paredes reflectantes, g = 9,8.
#  E1 Equilibrio: capa uniforme en reposo con h = 0,8 h_c (cumple ρ g h S < τ_y). Debe permanecer quieta: se mide el desplazamiento
#     del centro de masa y el transporte acumulado ∫|q| dA dt durante 600 s.
#  E2 Parada: bloque liberado; al final se evalúa el residuo local r = ρ g h |∇(z+h)| / τ_y en las celdas con h > 1 cm
#     (admisible si r ≤ 1, tolerancia por discretización) y la deriva del frente en los últimos 300 s.
#  E3 Reinicio: desde el depósito detenido de E2 se agrega mezcla aguas arriba (caso) o nada (control); se comparan los frentes.
#  E4 Convergencia espacial (dx 4, 2, 1 m) y temporal (CFL 1; 0,5; 0,25; 0,1) del alcance en E2.
import json, math, sys, numpy as np, anuga
RHO, G, S, TAU, ETA, K, N = 1700.0, 9.8, 0.05, 100.0, 1.0, 100.0, 0.025
HC = TAU / (RHO * G * S)

class Reo(anuga.Operator):
    def __init__(self, d): anuga.Operator.__init__(self, d); self.trans = 0.0
    def __call__(self):
        dt = self.domain.get_timestep(); h = np.maximum(self.stage_c - self.elev_c, 0); wet = h > 1e-3; hs = np.where(wet, h, 1.0)
        hu, hv = self.xmom_c, self.ymom_c; Us = np.where(wet, np.hypot(hu, hv) / hs, 0)
        A_ = TAU / (RHO * hs); B_ = K * ETA / (8 * RHO * hs ** 2); C_ = G * N ** 2 / hs ** (4 / 3)
        r = np.maximum(0, Us - dt * A_); Un = 2 * r / (1 + B_ * dt + np.sqrt((1 + B_ * dt) ** 2 + 4 * C_ * dt * r))
        f = np.where(wet & (Us > 0), Un / np.where(Us > 0, Us, 1), 0); hu *= f; hv *= f
        self.trans += dt * float(np.sum(np.hypot(hu, hv) * self.areas))
    def parallel_safe(self): return True
    def statistics(self): return ''
    def timestepping_statistics(self): return ''

def dominio(dx=2.0, cfl=0.25, L=600.0, W=20.0):
    d = anuga.rectangular_cross_domain(int(L / dx), int(W / dx), len1=L, len2=W)
    d.set_flow_algorithm('DE1'); d.set_cfl(cfl); d.set_minimum_storable_height(1e-3)
    d.set_quantity('elevation', lambda x, y: -S * x); d.set_quantity('friction', 0.0)
    Br = anuga.Reflective_boundary(d); d.set_boundary({'left': Br, 'right': Br, 'top': Br, 'bottom': Br}); return d
def estado(d):
    h = np.maximum(d.quantities['stage'].centroid_values - d.quantities['elevation'].centroid_values, 0); return h
def correr(d, T, dt_out=30.0):
    x = d.centroid_coordinates[:, 0]; hist = []
    for t in d.evolve(yieldstep=dt_out, finaltime=T):
        h = estado(d); w = h > 0.01; hist.append((float(t), float(x[w].max()) if w.any() else 0.0, float(np.sum(h * d.areas)), float(np.sum(h * x * d.areas) / max(1e-9, np.sum(h * d.areas)))))
    return np.array(hist)
def residuo(d):
    h = estado(d); st = d.quantities['stage']; st.compute_gradients()
    gx, gy = st.x_gradient, st.y_gradient; m = h > 0.01
    r = RHO * G * h[m] * np.hypot(gx[m], gy[m]) / TAU
    return {'r_mediana': round(float(np.median(r)), 3), 'r_p95': round(float(np.percentile(r, 95)), 3), 'frac_r_mayor_1,05': round(float(np.mean(r > 1.05)), 4)}

out = {'h_c_m': round(HC, 5), 'g': G}
# E1
d = dominio(); d.set_quantity('stage', lambda x, y: -S * x + np.where((x > 100) & (x < 500), 0.8 * HC, 0.0)); R1 = Reo(d)
h0 = correr(d, 600.0)
out['E1_equilibrio'] = {'desplaz_centro_masa_m': round(float(h0[-1, 3] - h0[0, 3]), 4), 'transporte_acumulado_m4': round(R1.trans, 4),
                        'volumen_ini_fin': [round(h0[0, 2], 3), round(h0[-1, 2], 3)]}
# E2 + E3
def bloque(dx=2.0, cfl=0.25, T=1500.0):
    d = dominio(dx, cfl); d.set_quantity('stage', lambda x, y: -S * x + np.where((x > 20) & (x < 40), 2.0, 0.0)); R = Reo(d)
    return d, correr(d, T), R
d2, h2, R2 = bloque()
i1200 = np.searchsorted(h2[:, 0], 1200.0)
out['E2_parada'] = {'frente_m': round(h2[-1, 1], 2), 'deriva_frente_ultimos_300s_m': round(h2[-1, 1] - h2[i1200, 1], 3), **residuo(d2)}
st0 = d2.quantities['stage'].centroid_values.copy(); xm0 = d2.quantities['xmomentum'].centroid_values.copy()
res3 = {}
for caso, Qf in (('control', 0.0), ('aporte', 2.0)):
    d = dominio(); d.set_quantity('stage', st0, location='centroids'); d.set_quantity('xmomentum', 0.0); d.set_quantity('ymomentum', 0.0); Reo(d)
    if Qf: anuga.Inlet_operator(d, anuga.Region(d, center=[10.0, 10.0], radius=4.0), Q=lambda t: Qf if t <= 60 else 0.0, default=0.0)
    hh = correr(d, 900.0); res3[caso] = {'frente_ini_m': round(hh[0, 1], 2), 'frente_fin_m': round(hh[-1, 1], 2), 'vol_fin_m3': round(hh[-1, 2], 2)}
out['E3_reinicio'] = res3 | {'reactivado': bool(res3['aporte']['frente_fin_m'] > res3['control']['frente_fin_m'] + 1.0),
                             'control_quieto': bool(abs(res3['control']['frente_fin_m'] - res3['control']['frente_ini_m']) < 1.0)}
# E4
conv = {}
for dx in (4.0, 2.0, 1.0):
    _, hh, _ = bloque(dx=dx, cfl=0.25); conv[f'dx={dx}'] = round(hh[-1, 1], 2)
for cfl in (1.0, 0.5, 0.25, 0.1):
    _, hh, _ = bloque(dx=2.0, cfl=cfl); conv[f'CFL={cfl}'] = round(hh[-1, 1], 2)
out['E4_convergencia_alcance_m'] = conv
json.dump(out, open('res/verif_v3.json', 'w'), indent=1, ensure_ascii=False); print(json.dumps(out, indent=1, ensure_ascii=False))
