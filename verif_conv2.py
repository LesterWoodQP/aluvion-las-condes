# Convergencia del alcance con el paso de tiempo: DE1 (RK2) vs DE0 (Euler) y CFL decreciente; + balance de volumen del inlet
import json, numpy as np, anuga, importlib.util
spec = importlib.util.spec_from_file_location('vp', 'verif_parada.py'); vp = importlib.util.module_from_spec(spec); spec.loader.exec_module(vp)
orig = anuga.rectangular_cross_domain
res = {}
for alg in ('DE1', 'DE0'):
    for cfl in ((0.1, 0.05) if alg == 'DE1' else (1.0, 0.5, 0.25, 0.1)):
        def fab(*a, **k):
            d = orig(*a, **k); d.set_flow_algorithm = (lambda d0: (lambda name: anuga.Domain.set_flow_algorithm(d0, alg)))(d); return d
        anuga.rectangular_cross_domain = fab
        hh, hm = vp.corrida(cfl=cfl, reinicio=False)
        res[f'{alg} CFL {cfl}'] = {'frente_m': round(hh[-1, 1], 2), 'h_medio': round(hm, 4), 'vol_ini': round(hh[0, 2], 2), 'vol_fin': round(hh[-1, 2], 2)}
        print(alg, cfl, res[f'{alg} CFL {cfl}'], flush=True)
anuga.rectangular_cross_domain = orig
json.dump(res, open('res/verif_conv2.json', 'w'), indent=1)
