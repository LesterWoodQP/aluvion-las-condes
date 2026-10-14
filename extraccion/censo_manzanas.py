# Manzanas del Censo 2017 (INE, servicio ArcGIS público 'Manzanas_censo_2017'; misma fuente que usa la aplicación Hirely Broker)
# para el área de estudio ampliada: viviendas y personas por manzana con su polígono. Salida: dem/censo/manzanas.geojson
import json, urllib.request, urllib.parse, sys
sys.path.insert(0, 'fuentes'); from registrar import registrar
URL = 'https://services9.arcgis.com/kKJR3Qt68ohAWuet/arcgis/rest/services/Manzanas_censo_2017/FeatureServer/0/query'
W, S, E, N = -70.565, -33.430, -70.485, -33.385
feats, off = [], 0
while True:
    q = {'where': '1=1', 'geometry': f'{W},{S},{E},{N}', 'geometryType': 'esriGeometryEnvelope', 'inSR': 4326, 'spatialRel': 'esriSpatialRelIntersects',
         'outFields': 'MANZENT_I,NOM_COMUNA,TOTAL_PERS,TOTAL_VIVI,NOM_CATEGO', 'returnGeometry': 'true', 'outSR': 4326, 'f': 'geojson', 'resultOffset': off, 'resultRecordCount': 2000}
    d = json.loads(urllib.request.urlopen(URL + '?' + urllib.parse.urlencode(q), timeout=120).read())
    feats += d.get('features', []); off += len(d.get('features', []))
    if not d.get('features') or not d.get('properties', {}).get('exceededTransferLimit', len(d['features']) == 2000): break
json.dump({'type': 'FeatureCollection', 'features': feats}, open('dem/censo/manzanas.geojson', 'w'))
viv = sum(f['properties']['TOTAL_VIVI'] or 0 for f in feats); per = sum(f['properties']['TOTAL_PERS'] or 0 for f in feats)
registrar('archivo', 'dem/censo/manzanas.geojson', f'INE Censo 2017 manzanas (ArcGIS Manzanas_censo_2017, fuente usada por Hirely Broker) en bbox {W},{S},{E},{N}: {len(feats)} manzanas, {viv} viviendas, {per} personas', 'dem/censo/manzanas.geojson')
print(len(feats), 'manzanas ·', viv, 'viviendas ·', per, 'personas ·', set(f['properties']['NOM_COMUNA'] for f in feats))
