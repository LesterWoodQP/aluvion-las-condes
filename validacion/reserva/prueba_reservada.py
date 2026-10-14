# Prueba con observaciones reservadas (no usadas para ajustar ni seleccionar). Protocolo: validacion/PROTOCOLO_VALIDACION.md.
#   python validacion/reserva/prueba_reservada.py congelar <id_candidato> [<id_referencia> ...]   fija candidato y referencias (una sola vez)
#   python validacion/reserva/prueba_reservada.py probar                                          ejecuta la prueba sobre lo congelado
# Toda ejecución se agrega a validacion/reserva/ejecuciones.jsonl (solo agregar) y se informa, aunque el resultado sea desfavorable.
import sys, os, json, hashlib, subprocess, datetime
import numpy as np
D = 'validacion/reserva/'; EQ = 'fuentes/visor_bbnn/equipamiento_afectado.geojson'
SHA_EQ = '1690627d7d07da10f2f56fff6d33b528bb94b0865104f47df9cd5e45f50e821c'   # registro probatorio, 11-oct-2026 10:17 UTC
EXCLUIR = ('Pontificia Universidad Catolica de Chile', 'Duoc')               # recintos ya usados en el ajuste (componente «sitios»)
H_UMBRAL, RADIO = 0.05, 15.0                                                 # fijados en el protocolo antes de mirar resultados
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
ahora = lambda: datetime.datetime.now().astimezone().isoformat(timespec='seconds')
def anotar(o):
    with open(D + 'ejecuciones.jsonl', 'a') as f: f.write(json.dumps(o, ensure_ascii=False) + '\n')
if sys.argv[1] == 'congelar':
    if os.path.exists(D + 'congelado.json'): sys.exit('ya hay un candidato congelado: cualquier cambio exige una entrada nueva justificada en el protocolo')
    ids = sys.argv[2:]; c = {'fecha': ahora(), 'candidato': ids[0], 'referencias': ids[1:],
         'sim_py_commit': subprocess.run(['git', 'log', '-1', '--format=%h', '--', 'sim.py'], capture_output=True, text=True).stdout.strip(),
         'npz_sha256': {i: sha(f'res/{i}.npz') for i in ids}}
    json.dump(c, open(D + 'congelado.json', 'w'), ensure_ascii=False, indent=1); anotar({'accion': 'congelar', **c}); print(c); sys.exit()
assert sha(EQ) == SHA_EQ, 'la capa reservada cambió respecto del registro probatorio'
c = json.load(open(D + 'congelado.json'))
for i, h in c['npz_sha256'].items(): assert sha(f'res/{i}.npz') == h, f'res/{i}.npz cambió después de congelarse'
from pyproj import Transformer
tf = Transformer.from_crs(4326, 32719, always_xy=True)
P = [(f['properties']['NOMBRE'], *tf.transform(*f['geometry']['coordinates'])) for f in json.load(open(EQ))['features'] if f['properties']['NOMBRE'] not in EXCLUIR]
res = {}
for i in [c['candidato']] + c['referencias']:
    z = np.load(f'res/{i}.npz'); x, y, h = z['cx'], z['cy'], z['hmax']
    m = h > H_UMBRAL; xs, ys = x[m], y[m]
    hit = [bool(np.any((xs - px) ** 2 + (ys - py) ** 2 <= RADIO ** 2)) for _, px, py in P]
    res[i] = {'n': len(P), 'alcanzados': int(sum(hit)), 'sensibilidad': round(sum(hit) / len(P), 3)}
o = {'accion': 'probar', 'fecha': ahora(), 'congelado': c['fecha'], 'resultado': res}
anotar(o); print(json.dumps(o, ensure_ascii=False, indent=1))
