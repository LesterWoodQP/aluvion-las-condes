# Búsqueda y archivo de escenas satelitales para la VALIDACIÓN INDEPENDIENTE (no se usan para calibrar).
# Guarda cada respuesta STAC con fecha UTC y hash en validacion/stac/ y registra en fuentes/registro_consultas.jsonl.
# Colecciones: Sentinel-2 L2A (Earth Search), Sentinel-1 GRD (Earth Search), Sentinel-1 RTC (Planetary Computer).
import json, hashlib, datetime, urllib.request, os, sys
sys.path.insert(0, 'fuentes'); from registrar import registrar
BBOX = [-70.553, -33.421, -70.490, -33.391]; RANGO = '2026-09-15T00:00:00Z/2026-10-31T00:00:00Z'
FUENTES = [('earth-search', 'https://earth-search.aws.element84.com/v1/search', 'sentinel-2-l2a'),
           ('earth-search', 'https://earth-search.aws.element84.com/v1/search', 'sentinel-1-grd'),
           ('planetary-computer', 'https://planetarycomputer.microsoft.com/api/stac/v1/search', 'sentinel-1-rtc')]
ahora = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'); res = {}
for srv, url, col in FUENTES:
    body = json.dumps({'collections': [col], 'bbox': BBOX, 'datetime': RANGO, 'limit': 100}).encode()
    d = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'}), timeout=60).read())
    f = f'validacion/stac/{col}_{ahora}.json'; json.dump(d, open(f, 'w'))
    items = [(x['properties']['datetime'][:16], x['properties'].get('eo:cloud_cover'), x['properties'].get('sat:orbit_state'), x['properties'].get('sat:relative_orbit'), x['id']) for x in d.get('features', [])]
    post = [i for i in items if i[0] >= '2026-10-08T20']
    registrar('stac', f'{srv}:{col} bbox={BBOX}', f'{len(items)} escenas; posteriores al evento: {[(i[0], i[1], i[2], i[3]) for i in post]}', f)
    res[col] = items
    print(col, len(items), 'posteriores:', post)
