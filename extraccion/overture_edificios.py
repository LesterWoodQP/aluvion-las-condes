# Huellas de edificios de Overture Maps (release 2026-09-23.1, tema buildings; combina OpenStreetMap, Microsoft y Google
# Open Buildings; licencia ODbL) para el área de estudio ampliada. Lee GeoParquet de S3 por filtro de bbox con DuckDB.
# Salida: dem/overture/edificios.geojson con fuente y altura/pisos cuando existen.
import duckdb, json
W, S, E, N = -70.565, -33.430, -70.485, -33.385
con = duckdb.connect(); con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial; SET s3_region='us-west-2';")
q = f"""
SELECT id, height, num_floors, sources[1].dataset AS fuente, ST_AsGeoJSON(geometry) AS geom
FROM read_parquet('s3://overturemaps-us-west-2/release/2026-09-23.1/theme=buildings/type=building/*', filename=true, hive_partitioning=1)
WHERE bbox.xmin > {W} AND bbox.xmax < {E} AND bbox.ymin > {S} AND bbox.ymax < {N}
"""
rows = con.execute(q).fetchall()
feats = [{'type': 'Feature', 'properties': {'id': r[0], 'height': r[1], 'num_floors': r[2], 'fuente': r[3]}, 'geometry': json.loads(r[4])} for r in rows]
json.dump({'type': 'FeatureCollection', 'features': feats}, open('dem/overture/edificios.geojson', 'w'))
from collections import Counter
print('edificios', len(feats), Counter(f['properties']['fuente'] for f in feats).most_common(), 'con altura', sum(1 for f in feats if f['properties']['height']))
