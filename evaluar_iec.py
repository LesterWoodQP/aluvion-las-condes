# IEC de corridas nuevas con el mismo cálculo de validacion/ajuste_oficial_20261011.json (solo observaciones de ajuste, grupo A del
# protocolo; NO usa el equipamiento reservado). Uso: python evaluar_iec.py v25 v28 ...  → corre calibrar.py si falta la fila y agrega/actualiza.
import sys, csv, json, subprocess, re
src = open('ajuste_escenarios.py').read(); ns = {}
exec(src[:src.index('M = {')].split('CORR = {')[0] + src[src.index('def perimetro_oficial'):src.index('CORR = {')], ns)
P = 'validacion/ajuste_oficial_20261011.json'; T = json.load(open(P)); por = {t['corrida']: t for t in T}
for c in sys.argv[1:]:
    filas = lambda: {r['corrida'][:-4]: r for r in csv.DictReader(open('res/corridas.csv')) if r['hstar'] == '0.05'}
    if c not in filas(): subprocess.run(['.venv/bin/python', 'calibrar.py', f'res/{c}.npz'], check=True, capture_output=True)
    r = filas()[c]; R, S, d = float(r['R_presencia']), float(r['S_sitios']), float(r['dist_PH_m'])
    comp = {'calles': round(R, 3), 'sitios': round(S, 3), 'alcance': round(max(0.0, min(1.0, 1 - (d - 200) / 1000)), 3), 'perimetro_oficial_urbano': round(ns['perimetro_oficial'](c), 3)}
    o = {'ajuste_oficial': round(100 * sum(comp.values()) / 4), 'corrida': c, **comp, 'criterios_originales': int(R >= 0.6) + int(S >= 0.75) + int(d <= 200) + int(comp['perimetro_oficial_urbano'] >= 0.5), 'dist_PH_m': round(d)}
    por[c] = {**por.get(c, {}), **o}; print(o)
json.dump(sorted(por.values(), key=lambda t: -t['ajuste_oficial']), open(P, 'w'), ensure_ascii=False, indent=1)
