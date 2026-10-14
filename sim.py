# Simulación 2D del flujo de barro (aluvión de Las Condes, 8-oct-2026) con ANUGA + reología cuadrática (O'Brien & Julien 1988).
# v3 — incorpora las correcciones de las revisiones A1 y A2 (revision/ronda_A1_informe.md, ronda_A2_informe.md).
#
# Ecuaciones (aguas someras, mezcla homogénea de densidad constante, lecho fijo; ANUGA resuelve q = h u):
#   ∂h/∂t + ∇·q = S_h,     ∂q/∂t + ∇·(q⊗q/h + ½ g h² I) = −g h ∇z − τ_b/ρ_m + S_h u_in
#   (al dividir por ρ_m constante no aparece ningún factor ρ_m/ρ_w en presión ni gravedad — A1 §2)
# Resistencia de la mezcla (cierre cuadrático de FLO-2D, ecs. 4.25–4.31):
#   S_f = τ_y/(ρ_m g h) + K η U/(8 ρ_m g h²) + n_td² U²/h^{4/3},   τ_b/ρ_m = g h S_f · u/U
#   τ_y = 0,1·α₂ e^{β₂ C_v,matriz} [Pa],  η = 0,1·α₁ e^{β₁ C_v,matriz} [Pa·s]   (C_v de la matriz fina — A1 §1)
#   ρ_m = ρ_w + C_v,total (ρ_s − ρ_w)                                          (C_v total de la mezcla — A1 §1)
# Paso fraccionado de resistencia, totalmente implícito local (A1 §3):  U' + Δt(a + bU' + cU'²) = U*
#   a = τ_y/(ρ_m h), b = K η/(8 ρ_m h²), c = g n_td²/h^{4/3};  r = (U* − Δt a)₊;  U' = 2r / (1 + bΔt + √((1+bΔt)² + 4cΔt r))
#   Propiedades: 0 ≤ U' ≤ U*, conserva dirección, disipa energía, no altera h (conserva volumen). Primer orden en el tiempo.
#   Parada: si |q*| ≤ Δt τ_y/ρ_m ⇒ q = 0 (proyección local); reinicio libre cuando la fuerza motriz supera el umbral.
#   Verificación de parada/reinicio y convergencia: verif_parada.py, convergencia.py.
# Resistencia por superficie (A1 §4): calles (K_c, n_c) y resto/cauce (K_o, n_o).
# Entrada (A1 §8.2): fuente de mezcla con velocidad impuesta en la dirección del cauce. Hidrograma triangular con
#   restricciones 0 < t_p < T_B = 2V/Q_p y t_fin ≥ T_B + recesión (A1 §8.1); balance de volumen registrado (A1 §8.3).
import sys, os, json, math, time, argparse, numpy as np, anuga
from scipy.interpolate import RegularGridInterpolator
from scipy import ndimage as nd
from pyproj import Transformer

ap = argparse.ArgumentParser()
ap.add_argument('--qp', type=float, default=40.0, help='caudal pico de mezcla (m³/s)')
ap.add_argument('--vol', type=float, default=60000.0, help='volumen total de mezcla (m³)')
ap.add_argument('--tp', type=float, default=600.0, help='tiempo al pico (s)')
ap.add_argument('--cv', type=float, default=0.40, help='C_v de la matriz fina (reología)')
ap.add_argument('--cv_faldeo', type=float, default=None, help='C_v (matriz y total) del barro en la zona del faldeo: brazo sur, campus U. Andes, Álvaro del Portillo y ladera oriente (flujo más líquido, sin escombros urbanos)')
ap.add_argument('--cvt', type=float, default=None, help='C_v total de la mezcla (densidad); por defecto = cv')
ap.add_argument('--suelo', default='glenwood2b', help='muestra reológica (tabla FLO-2D 2021/2023)')
ap.add_argument('--Kc', type=float, default=100.0, help='K laminar en calles pavimentadas')
ap.add_argument('--nc', type=float, default=0.025, help='n_td en calles')
ap.add_argument('--Ko', type=float, default=400.0, help='K laminar en el resto (suelo, jardines, cauce)')
ap.add_argument('--no', type=float, default=0.050, help='n_td en el resto')
ap.add_argument('--Kp', type=float, default=4000.0, help='K laminar en edificios porosos (máscara POROSO del terreno)')
ap.add_argument('--np_', type=float, default=0.20, help='n_td en edificios porosos: el barro entra a las casas, con mucha resistencia')
ap.add_argument('--uin', type=float, default=2.0, help='velocidad de entrada en la dirección del cauce (m/s)')
ap.add_argument('--fino', type=float, default=50.0, help='área máx. de triángulo en el corredor (m²)')
ap.add_argument('--grueso', type=float, default=600.0)
ap.add_argument('--cfl', type=float, default=1.0)
ap.add_argument('--tfin', type=float, default=None, help='duración; por defecto T_B + 1200 s')
ap.add_argument('--sigma', type=float, default=0.0, help='Monte Carlo de terreno: desviación (m) del error correlacionado')
ap.add_argument('--ell', type=float, default=60.0, help='largo de correlación (m)')
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--dominio', default=None, help='microsimulación: "lat_s,lon_o,lat_n,lon_e"; malla fina (--fino) en todo el rectángulo y desagüe libre en los 4 bordes')
ap.add_argument('--punto', default=None, help='origen P: "lat,lon,lat_dir,lon_dir" (centro de la fuente y punto hacia donde apunta su velocidad)')
ap.add_argument('--origen', default='H1', help='H1: abanico · H2: Fco. Bulnes Correa · H3: aporte distribuido H1+S1+S2 según área de cuenca (cuenca.json)')
ap.add_argument('--fsup', type=float, default=0.5, help='H4: fracción del aporte de H1 que sale en superficie en el abanico (el resto sigue por el ducto y rebalsa en Fco. Bulnes Correa)')
ap.add_argument('--h1', type=str, default=None, help='lat,lon,lat,lon: punto de inyección y dirección del hidrograma H1 (p. ej. aguas arriba del tapón de árboles)')
ap.add_argument('--fs1', type=float, default=None, help='H3/H4: fracción total asignada a S1 (brazo sur); reescala H1 manteniendo S2')
ap.add_argument('--fs2', type=float, default=None, help='H3/H4: fracción total asignada a S2 (escurrimiento local hacia La Plaza Sur); por defecto, la proporción de área')
ap.add_argument('--terreno', default='terreno.npz', help='terreno.npz o terreno_tallado.npz (cauce del parque lineal tallado)')
ap.add_argument('--lluvia', type=float, default=0.0, help='H5: lluvia efectiva sobre la ladera oriente de La Plaza Sur (mm/h de mezcla = i·C/(1−Cv))')
ap.add_argument('--lluvia_neta', action='store_true', help='descuenta del polígono de lluvia las cuencas aportantes (H1, S1, S2), cuya escorrentía ya está en los hidrogramas: evita el doble conteo')
ap.add_argument('--lluvia_faldeo', action='store_true', help='lluvia sobre el faldeo completo (campus, La Plaza Sur, ladera oriente) en vez de solo la ladera oriente')
ap.add_argument('--lluvia_todo', action='store_true', help='microsimulación: lluvia sobre todo el dominio (no solo la ladera oriente)')
ap.add_argument('--sin_fuentes', action='store_true', help='sin hidrogramas de entrada (solo lluvia sobre la malla)')
ap.add_argument('--tlluvia', type=float, default=3600.0, help='H5: duración de la lluvia sobre la ladera (s)')
ap.add_argument('--colector', type=float, default=None, help='capacidad del colector en la embocadura de Fco. Bulnes Correa (m³/s): sumidero que retira hasta ese caudal de mezcla (requiere terreno con el cauce tallado)')
ap.add_argument('--radio_colector', type=float, default=12.0, help='radio de captación del colector-sumidero (m)')
ap.add_argument('--hietograma', default=None, help='CSV «minuto,mm» en intervalos de 30 min desde t=0: lluvia variable en el tiempo (reemplaza --lluvia/--tlluvia; mm de mezcla, misma convención)')
ap.add_argument('--f_lluvia', type=float, default=1.0, help='factor sobre el hietograma (p. ej. gradiente orográfico entre la estación y el faldeo)')
ap.add_argument('--t0_fuentes', type=float, default=0.0, help='retraso (s) del inicio de los hidrogramas respecto de t=0 (para alinearlos con el hietograma)')
ap.add_argument('--refinar', default=None, help='"lat_s,lon_o,lat_n,lon_e,area": región con malla más fina (área máx. de triángulo en m²) dentro del corredor')
ap.add_argument('--dtmax', type=float, default=0.5, help='paso de tiempo máximo (s): evita pasos enormes con el dominio casi seco (película de lluvia), que crean masa al corregir celdas negativas')
ap.add_argument('--salida', default='res/run')
a = ap.parse_args()
a.cvt = a.cv if a.cvt is None else a.cvt
assert 0 <= a.cv <= a.cvt < 1, 'debe cumplirse 0 ≤ Cv,matriz ≤ Cv,total < 1 (A2 §1)'

# (α₁ poise, β₁, α₂ dyn/cm², β₂) — FLO-2D Reference Manual 2021, tabla 13; Glenwood 2 en tres variantes documentales (A1 §1)
SUELOS = {'glenwood1': (0.00283, 23.0, 0.0345, 20.1), 'glenwood2a': (0.0648, 6.20, 0.0765, 16.9),
          'glenwood2b': (0.648, 6.20, 0.0765, 16.9), 'glenwood2c': (0.648, 8.20, 0.0765, 16.9),
          'aspen1': (0.0360, 22.1, 0.181, 25.7), 'aspen2': (0.0538, 14.5, 2.72, 10.4)}
a1, b1, a2, b2 = SUELOS[a.suelo]
RHO_W, RHO_S = 1000.0, 2650.0
G = 9.8   # = anuga.config.g (A2 §2: gravedad única en todo el modelo)
RHO_M = RHO_W + a.cvt * (RHO_S - RHO_W)
TAU_Y = 0.1 * a2 * math.exp(b2 * a.cv); ETA = 0.1 * a1 * math.exp(b1 * a.cv)
TB = 2 * a.vol / a.qp
HIETO = None
if a.hietograma:   # lluvia acumulada D(t) lineal por tramos de 30 min (volumen aplicado exacto)
    _hv = np.loadtxt(a.hietograma, delimiter=',', comments='#'); _hv = _hv[np.argsort(_hv[:, 0])]
    HIETO = (np.r_[_hv[:, 0] * 60.0, _hv[-1, 0] * 60.0 + 1800.0], np.r_[0.0, np.cumsum(_hv[:, 1] * a.f_lluvia / 1000.0)])
    a.tlluvia = float(HIETO[0][-1]); a.lluvia = float(HIETO[1][-1] * 1000.0 / (a.tlluvia / 3600.0))   # media (mm/h) solo para informe
assert 0 < a.tp < TB, f'hidrograma inválido: t_p={a.tp} debe ser < T_B={TB:.0f}'
a.tfin = a.tfin or max(a.t0_fuentes + TB, a.tlluvia if a.lluvia > 0 else 0.0) + 1200.0   # cubre todo el hidrograma y toda la lluvia
assert a.tfin >= a.t0_fuentes + TB or os.environ.get('SIM_PRUEBA'), 't_fin debe cubrir todo el hidrograma'
print(f'{a.suelo} Cv_matriz={a.cv} Cv_total={a.cvt} ρm={RHO_M:.0f} kg/m³ τy={TAU_Y:.1f} Pa η={ETA:.3f} Pa·s · '
      f'calles K={a.Kc} n={a.nc} · resto K={a.Ko} n={a.no} · Qp={a.qp} m³/s V={a.vol:.0f} m³ T_B={TB:.0f} s t_fin={a.tfin:.0f} s', flush=True)

T = np.load(a.terreno); X0, Y0, DX = float(T['X0']), float(T['Y0']), float(T['DX'])
gx = X0 + (np.arange(int(T['NX'])) + 0.5) * DX; gy = Y0 + (np.arange(int(T['NY'])) + 0.5) * DX
ELEV = T['ELEV'].astype(np.float64)
if a.sigma > 0:   # error de terreno espacialmente correlacionado (gaussiano), A1 §6 — sensibilidad, no intervalo medido
    rng = np.random.default_rng(a.seed); w = rng.standard_normal(ELEV.shape)
    e = nd.gaussian_filter(w, a.ell / DX / math.sqrt(2)); e *= a.sigma / e.std()
    ELEV = ELEV + e + rng.normal(0, a.sigma * 0.25)
fz = RegularGridInterpolator((gy, gx), ELEV, bounds_error=False, fill_value=None)
fcalle = RegularGridInterpolator((gy, gx), T['CALLE'].astype(np.float64), bounds_error=False, fill_value=0.0)
tf = Transformer.from_crs('EPSG:4326', 'EPSG:32719', always_xy=True)
U = lambda lat, lon: list(tf.transform(lon, lat))

m = 30.0
bound = [[gx[0] + m, gy[0] + m], [gx[-1] - m, gy[0] + m], [gx[-1] - m, gy[-1] - m], [gx[0] + m, gy[-1] - m]]
corredor = [U(-33.3945, -70.4903), U(-33.4120, -70.4903), U(-33.4185, -70.5500), U(-33.4020, -70.5500)]   # incluye S1 y La Plaza Sur
if 'v4' in a.terreno:   # dominio ampliado: corredor hasta Quebrada Apoquindo, Hospital Dipreca, Paul Harris y Rotonda Atenas
    corredor = [U(-33.3945, -70.4903), U(-33.4130, -70.4903), U(-33.4235, -70.5250), U(-33.4235, -70.5585), U(-33.4020, -70.5585)]
if a.dominio:   # microsimulación local
    la0, lo0, la1, lo1 = map(float, a.dominio.split(',')); x0_, y0_ = U(la0, lo0); x1_, y1_ = U(la1, lo1)
    bound = [[x0_, y0_], [x1_, y0_], [x1_, y1_], [x0_, y1_]]; corredor = bound
REFINO = []
if a.refinar:   # región anidada dentro del corredor (no debe cruzar sus bordes)
    _r = list(map(float, a.refinar.split(','))); _p0 = U(_r[0], _r[1]); _p1 = U(_r[2], _r[3])
    REFINO = [[[[_p0[0], _p0[1]], [_p1[0], _p0[1]], [_p1[0], _p1[1]], [_p0[0], _p1[1]]], _r[4]]]
    from matplotlib.path import Path as _P; assert _P(corredor).contains_points([[_p0[0], _p0[1]], [_p1[0], _p1[1]], [_p0[0], _p1[1]], [_p1[0], _p0[1]]]).all(), 'la región refinada debe quedar dentro del corredor'
domain = anuga.create_domain_from_regions(bound, boundary_tags={'s': [0], 'e': [1], 'n': [2], 'w': [3]},
                                          maximum_triangle_area=a.grueso, interior_regions=[[corredor, a.fino]] + REFINO, use_cache=False, verbose=False)
domain.set_name(a.salida.split('/')[-1]); domain.set_datadir(a.salida.rsplit('/', 1)[0])
domain.set_flow_algorithm('DE1'); domain.set_minimum_storable_height(0.01); domain.set_CFL(a.cfl)
gr = domain.geo_reference
cx, cy = domain.centroid_coordinates[:, 0] + gr.xllcorner, domain.centroid_coordinates[:, 1] + gr.yllcorner
vx = domain.vertex_coordinates[:, 0] + gr.xllcorner; vy = domain.vertex_coordinates[:, 1] + gr.yllcorner
domain.set_quantity('elevation', fz(np.c_[vy, vx]).reshape(-1, 3), location='vertices')
domain.set_quantity('friction', 0.0); domain.set_quantity('stage', expression='elevation')
if a.dtmax > 0: domain.set_evolve_max_timestep(a.dtmax)
# Bordes de salida S y O: desagüe libre (Dirichlet con nivel bajo el lecho → solo puede salir masa). El Transmissive_boundary
# de ANUGA creaba masa espuria cuando el frente llegaba al borde sur (+20 % en la corrida e02 del cribado v3c).
Br = anuga.Reflective_boundary(domain); Bt = anuga.Dirichlet_boundary([float(np.min(domain.quantities['elevation'].centroid_values)) - 50.0, 0.0, 0.0])
domain.set_boundary({'s': Bt, 'e': Bt, 'n': Bt, 'w': Bt} if a.dominio else {'s': Bt, 'e': Br, 'n': Br, 'w': Bt})
es_calle = fcalle(np.c_[cy, cx]) > 0.5
Kf = np.where(es_calle, a.Kc, a.Ko); nf = np.where(es_calle, a.nc, a.no)
if 'POROSO' in T.files:   # edificios porosos: almacenan barro (entra por puertas, ventanas y muros caídos) y lo frenan
    es_poro = RegularGridInterpolator((gy, gx), T['POROSO'].astype(np.float64), bounds_error=False, fill_value=0.0)(np.c_[cy, cx]) > 0.5
    Kf = np.where(es_poro, a.Kp, Kf); nf = np.where(es_poro, a.np_, nf); print(f'edificios porosos: {es_poro.mean() * 100:.1f} % de los triángulos', flush=True)
print('triángulos', len(domain), f'· en calle {es_calle.mean() * 100:.1f} %', flush=True)

def Q(t):
    if t <= a.tp: return a.qp * t / a.tp
    if t <= TB: return a.qp * (TB - t) / (TB - a.tp)
    return 0.0
PUNTOS = {'P': (tuple(map(float, a.punto.split(',')[:2])), tuple(map(float, a.punto.split(',')[2:]))) if a.punto else None,
          'H1': ((-33.40030, -70.49960), (-33.40060, -70.50080)),     # cauce principal → abanico (eje OSM)
          'H2': ((-33.40590, -70.51630), (-33.40930, -70.52218)),     # salida del ducto en Fco. Bulnes Correa → tramo entubado SW
          'S1': ((-33.40703, -70.49092), (-33.40500, -70.49280)),     # cauce sur: entrada del ducto en el borde urbano → campus U. Andes
          'S2': ((-33.40870, -70.49990), (-33.40864, -70.50048))}     # quebradas cortas → Av. La Plaza Sur (Clínica U. Andes)
if a.h1: _h = list(map(float, a.h1.split(','))); PUNTOS['H1'] = ((_h[0], _h[1]), (_h[2], _h[3]))   # H1 reubicado
if a.origen in ('H3', 'H4'):
    _cu = json.load(open('cuenca.json')); _A = sum(_cu[k]['area_km2'] for k in ('H1', 'S1', 'S2'))
    fr = {k: _cu[k]['area_km2'] / _A for k in ('H1', 'S1', 'S2')}
    if a.fs2 is not None:   # reasigna S2 y reescala H1 y S1 manteniendo su proporción
        resto = 1 - fr['S2']; fr = {'H1': fr['H1'] / resto * (1 - a.fs2), 'S1': fr['S1'] / resto * (1 - a.fs2), 'S2': a.fs2}
    if a.fs1 is not None: fr = {'H1': 1 - a.fs1 - fr['S2'], 'S1': a.fs1, 'S2': fr['S2']}   # brazo sur con más aporte que su área
    if a.origen == 'H3': FUENTES = [(k, fr[k]) for k in ('H1', 'S1', 'S2')]
    else: FUENTES = [('H1', fr['H1'] * a.fsup), ('H2', fr['H1'] * (1 - a.fsup)), ('S1', fr['S1']), ('S2', fr['S2'])]
else: FUENTES = [(a.origen, 1.0)]
class Fuente(anuga.Operator):
    """Fuente de mezcla (A2 §1): h⁺ = h⁻ + Δh,  q⁺ = q⁻ + Δh·u_in. Sin forzamiento cuando Q = 0. Integra exactamente el hidrograma."""
    def __init__(self, domain, centro, radio, uvec, frac=1.0):
        anuga.Operator.__init__(self, domain); self.frac = frac
        d2 = (cx - centro[0]) ** 2 + (cy - centro[1]) ** 2; self.idx = np.nonzero(d2 <= radio ** 2)[0]
        self.A = float(np.sum(self.areas[self.idx])); self.u = np.array(uvec); self.vol = 0.0
    def __call__(self):
        t0 = self.domain.get_time(); dt = self.domain.get_timestep(); t1 = t0 + dt
        dv = self.frac * (vol_hidro(t1) - vol_hidro(t0))   # cada fuente recibe su fracción del mismo hidrograma
        if dv <= 0: return
        dh = dv / self.A; self.stage_c[self.idx] += dh
        self.xmom_c[self.idx] += dh * self.u[0]; self.ymom_c[self.idx] += dh * self.u[1]; self.vol += dv
    def parallel_safe(self): return False
    def statistics(self): return 'Fuente de mezcla'
    def timestepping_statistics(self): return ''
def vol_hidro(t):   # ∫₀ᵗ Q dt exacta para el triángulo (desplazado t0_fuentes)
    t = t - a.t0_fuentes
    if t <= 0: return 0.0
    if t <= a.tp: return 0.5 * a.qp * t * t / a.tp
    if t <= TB: return a.vol - 0.5 * a.qp * (TB - t) ** 2 / (TB - a.tp)
    return a.vol
fuentes = []
if a.sin_fuentes: FUENTES = []
for k, fr in FUENTES:
    (p_lat, p_lon), (q_lat, q_lon) = PUNTOS[k]; p_in = U(p_lat, p_lon)
    d_in = np.array(U(q_lat, q_lon)) - np.array(p_in); d_in /= np.linalg.norm(d_in)
    fuentes.append(Fuente(domain, p_in, 14.0, [float(a.uin * d_in[0]), float(a.uin * d_in[1])], fr))
print('fuentes:', [(k, round(fr, 3)) for k, fr in FUENTES])
# H5: lluvia sobre la malla en la ladera oriente que drena a La Plaza Sur (entre La Plaza y el borde E, del campus a Vital Apoquindo)
LADERA = [U(-33.4045, -70.5030), U(-33.4045, -70.4903), U(-33.4125, -70.4903), U(-33.4125, -70.5030)]
class Lluvia(anuga.Operator):
    """Lluvia efectiva uniforme sobre un polígono: h⁺ = h⁻ + r·Δt (sin momento); volumen aplicado exacto."""
    def __init__(self, domain, poly, r, T):
        anuga.Operator.__init__(self, domain); from matplotlib.path import Path
        self.idx = np.nonzero(Path(poly).contains_points(np.c_[cx, cy]))[0]; self.r, self.T, self.vol = r, T, 0.0
        self.A = float(np.sum(self.areas[self.idx]))
    def __call__(self):
        t0 = self.domain.get_time(); dt = min(self.domain.get_timestep(), max(0.0, self.T - t0))
        if dt <= 0: return
        dh = (np.interp(t0 + dt, *HIETO) - np.interp(t0, *HIETO)) if HIETO is not None else self.r * dt
        if dh <= 0: return
        self.stage_c[self.idx] += dh; self.vol += dh * self.A
    def parallel_safe(self): return False
    def statistics(self): return 'Lluvia sobre ladera'
    def timestepping_statistics(self): return ''
class Colector(anuga.Operator):
    """Embocadura del colector como sumidero: retira de las celdas de la boca hasta Qc·Δt de mezcla por paso (lo que haya disponible).
    Representa un colector que conduce bajo tierra hasta su capacidad Qc y no devuelve flujo a la superficie dentro del dominio."""
    def __init__(self, domain, centro, radio, Qc):
        anuga.Operator.__init__(self, domain)
        d2 = (cx - centro[0]) ** 2 + (cy - centro[1]) ** 2; self.idx = np.nonzero(d2 <= radio ** 2)[0]; self.Qc, self.vol, self.qmax = Qc, 0.0, 0.0
    def __call__(self):
        dt = self.domain.get_timestep(); i = self.idx; Ai = self.areas[i]
        h = np.maximum(self.stage_c[i] - self.elev_c[i], 0.0); disp = float(np.sum(h * Ai))
        if disp <= 0 or self.Qc <= 0: return
        quitar = min(disp, self.Qc * dt); f = 1.0 - quitar / disp
        hn = h * f; self.stage_c[i] = self.elev_c[i] + hn; self.xmom_c[i] *= f; self.ymom_c[i] *= f
        self.vol += quitar; self.qmax = max(self.qmax, quitar / dt)
    def parallel_safe(self): return False
    def statistics(self): return 'Colector (sumidero)'
    def timestepping_statistics(self): return ''
# (el volumen retirado por el colector se descuenta del volumen aplicado en el balance)
colector = None
if a.colector is not None:
    colector = Colector(domain, U(-33.40586, -70.51609), a.radio_colector, a.colector)
    print(f'colector en la embocadura: capacidad {a.colector} m³/s sobre {len(colector.idx)} celdas')
lluvia_op = None
if a.lluvia > 0:
    FALDEO_LL = [U(-33.4013, -70.5070), U(-33.4013, -70.4903), U(-33.4130, -70.4903), U(-33.4130, -70.5070)]   # mismo polígono que la reología por zona
    lluvia_op = Lluvia(domain, (bound if a.lluvia_todo else (FALDEO_LL if a.lluvia_faldeo else LADERA)), a.lluvia / 1000.0 / 3600.0, a.tlluvia)
    if a.lluvia_neta:   # quitar celdas dentro de las cuencas aportantes (su escorrentía ya entra por los hidrogramas)
        from shapely.geometry import shape as _sh
        from shapely.ops import unary_union as _uu, transform as _st
        from shapely import contains_xy as _cxy
        _C = _uu([_sh(f['geometry']) for k in ('H1', 'S1', 'S2') for f in json.load(open(f'cuenca_{k}.geojson'))['features']])
        _dentro = _cxy(_C, cx[lluvia_op.idx], cy[lluvia_op.idx]); lluvia_op.idx = lluvia_op.idx[~_dentro]; lluvia_op.A = float(np.sum(lluvia_op.areas[lluvia_op.idx]))
        print(f'lluvia neta: se excluyen {int(_dentro.sum())} triángulos dentro de las cuencas aportantes', flush=True)
    print(f'lluvia sobre ladera: {a.lluvia} mm/h durante {a.tlluvia:.0f} s sobre {lluvia_op.A / 1e6:.3f} km² → {a.lluvia / 1000 * lluvia_op.A * a.tlluvia / 3600:.0f} m³')

class Reologia(anuga.Operator):
    """Resistencia de flujo de barro (O'Brien & Julien), implícita local + registro de máximos y llegada."""
    def __init__(self, domain):
        anuga.Operator.__init__(self, domain)
        n = len(self.stage_c); z = np.zeros(n)
        self.hmax, self.vmax, self.pdin, self.mflux, self.qmax = z.copy(), z.copy(), z.copy(), z.copy(), z.copy()
        self.tarr = np.full(n, np.nan); self.paradas = 0; self.ux, self.uy = z.copy(), z.copy()   # dirección de la velocidad en el instante de V máx
    def __call__(self):
        dt = self.domain.get_timestep(); t1 = self.domain.get_time() + dt      # el estado corresponde al final del paso (A1 §8.5)
        h = np.maximum(self.stage_c - self.elev_c, 0.0); wet = h > 1e-3
        hs = np.where(wet, h, 1.0); hu, hv = self.xmom_c, self.ymom_c
        Us = np.where(wet, np.hypot(hu, hv) / hs, 0.0)
        A_ = TAU_Y_c / (RHO_c * hs); B_ = Kf * ETA_c / (8.0 * RHO_c * hs ** 2); C_ = G * nf ** 2 / hs ** (4.0 / 3.0)
        r = np.maximum(0.0, Us - dt * A_)
        Un = 2.0 * r / (1.0 + B_ * dt + np.sqrt((1.0 + B_ * dt) ** 2 + 4.0 * C_ * dt * r))
        f = np.where(wet & (Us > 0), Un / np.where(Us > 0, Us, 1.0), 0.0)
        self.paradas += int(np.sum(wet & (Us > 0) & (r == 0)))
        hu *= f; hv *= f
        s = h > 0.05
        nuevo = s & (Un > self.vmax); hsn = np.where(nuevo, hs, 1.0)
        self.ux = np.where(nuevo, hu / hsn, self.ux); self.uy = np.where(nuevo, hv / hsn, self.uy)
        self.hmax = np.maximum(self.hmax, h); self.vmax = np.maximum(self.vmax, np.where(s, Un, 0.0))
        self.pdin = np.maximum(self.pdin, np.where(s, 0.5 * RHO_c * Un ** 2, 0.0))       # presión dinámica ½ρU² (A1 §8.4)
        self.mflux = np.maximum(self.mflux, np.where(s, RHO_c * h * Un ** 2, 0.0))       # flujo de momento por ancho ρhU² (N/m), instantáneo
        self.qmax = np.maximum(self.qmax, np.where(s, h * Un, 0.0))
        arr = np.isnan(self.tarr) & s; self.tarr[arr] = t1
    def parallel_safe(self): return True
    def statistics(self): return "Reología O'Brien-Julien (implícita local)"
    def timestepping_statistics(self): return ''
# reología por zona: el faldeo (brazo sur, campus, Álvaro del Portillo, Clínica U. Andes, ladera oriente) puede llevar un barro más líquido
TAU_Y_c = np.full(len(cx), TAU_Y); ETA_c = np.full(len(cx), ETA); RHO_c = np.full(len(cx), RHO_M)
if a.cv_faldeo is not None:
    from matplotlib.path import Path as _P
    FALDEO = [U(-33.4013, -70.5070), U(-33.4013, -70.4903), U(-33.4130, -70.4903), U(-33.4130, -70.5070)]
    mF = _P(FALDEO).contains_points(np.c_[cx, cy])
    TAU_Y_c[mF] = 0.1 * a2 * math.exp(b2 * a.cv_faldeo); ETA_c[mF] = 0.1 * a1 * math.exp(b1 * a.cv_faldeo); RHO_c[mF] = RHO_W + a.cv_faldeo * (RHO_S - RHO_W)
    print(f'faldeo con Cv {a.cv_faldeo}: {mF.mean() * 100:.1f} % de los triángulos · τy {TAU_Y_c[mF][0]:.2f} Pa · η {ETA_c[mF][0]:.3f} Pa·s · ρ {RHO_c[mF][0]:.0f} kg/m³', flush=True)
R = Reologia(domain)

t0 = time.time(); snaps = []; vin = 0.0; tprev = 0.0; balance = []
for t in domain.evolve(yieldstep=60.0, finaltime=a.tfin):
    h = np.maximum(domain.quantities['stage'].centroid_values - domain.quantities['elevation'].centroid_values, 0)
    # volumen entrado: integral exacta del hidrograma triangular entre tprev y t
    vin = sum(f.vol for f in fuentes) + (lluvia_op.vol if lluvia_op is not None else 0.0) - (colector.vol if colector is not None else 0.0); vol = float(np.sum(h * domain.areas)); snaps.append(h.astype(np.float16))
    bflux = float(domain.get_boundary_flux_integral()) if hasattr(domain, 'get_boundary_flux_integral') else float('nan')
    balance.append((float(t), vin, vol, bflux))
    if int(t) % 600 == 0: print(f'  t={t:5.0f} s · entrado {vin:8.0f} m³ · en malla {vol:8.0f} m³ · mojado {np.sum(domain.areas[h > 0.05]) / 1e4:6.1f} ha · {time.time() - t0:5.0f} s reales', flush=True)
bal = np.array(balance)
np.savez_compressed(a.salida + '.npz', cx=cx, cy=cy, area=domain.areas, hmax=R.hmax, vmax=R.vmax, ux=R.ux, uy=R.uy, pdin=R.pdin, mflux=R.mflux, qmax=R.qmax,
                    tarr=R.tarr, snaps=np.array(snaps), balance=bal, calle=es_calle, elev=domain.quantities['elevation'].centroid_values,
                    params=json.dumps(vars(a) | {'rho_m': RHO_M, 'tau_y': TAU_Y, 'eta': ETA, 'TB': TB, 'version': 'v3-A2-N1', 'vol_colector': (colector.vol if colector is not None else 0.0)}),
                    tri=domain.triangles, vx=vx.reshape(-1, 3), vy=vy.reshape(-1, 3))
err = (bal[-1, 2] - bal[-1, 1] - bal[-1, 3]) / max(1.0, bal[-1, 1])   # malla − (aplicado + flujo neto entrante por bordes)
print(f'colector: retiró {colector.vol:.0f} m³, caudal máx {colector.qmax:.1f} m³/s') if colector is not None else None
print(f'listo en {time.time() - t0:.0f} s · h>5 cm: {np.sum(domain.areas[R.hmax > 0.05]) / 1e4:.1f} ha · h máx {R.hmax.max():.2f} m · '
      f'V máx {R.vmax.max():.1f} m/s · aplicado {bal[-1, 1]:.0f} m³ · flujo neto por bordes {bal[-1, 3]:+.1f} m³ · residuo de balance {err * 100:+.3f} % · paradas {R.paradas}')
