# Registro probatorio de consultas: cada consulta (búsqueda, página, dato descargado) queda con fecha/hora UTC, origen,
# dato extraído y una captura con hash sha256. Uso:
#   python registrar.py url <URL> "<dato usado>"            (descarga y guarda la página)
#   python registrar.py busqueda "<consulta>" "<resultado>" (búsqueda web: guarda la consulta y lo obtenido)
#   python registrar.py archivo <ruta> "<descripción>"      (dato descargado por otro medio)
import sys, json, hashlib, datetime, os, re, subprocess, urllib.parse
REG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'registro_consultas.jsonl')
CAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'capturas')
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def ahora(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
def registrar(tipo, origen, dato, archivo=None):
    e = {'fecha_utc': ahora(), 'tipo': tipo, 'origen': origen, 'dato_usado': dato}
    if archivo and os.path.exists(archivo): e |= {'captura': os.path.relpath(archivo, os.path.dirname(REG)), 'sha256': sha(archivo), 'bytes': os.path.getsize(archivo)}
    open(REG, 'a').write(json.dumps(e, ensure_ascii=False) + '\n'); return e
if __name__ == '__main__':
    tipo = sys.argv[1]
    if tipo == 'url':
        url, dato = sys.argv[2], sys.argv[3]
        nombre = re.sub(r'[^\w.-]+', '_', urllib.parse.urlparse(url).netloc + urllib.parse.urlparse(url).path)[:150] + '.html'
        dest = os.path.join(CAP, nombre)
        subprocess.run(['curl', '-s', '-L', '--max-time', '40', '-A', 'Mozilla/5.0 (estudio aluvion Las Condes)', '-o', dest, url])
        print(json.dumps(registrar('pagina', url, dato, dest), ensure_ascii=False))
    elif tipo == 'busqueda': print(json.dumps(registrar('busqueda_web', sys.argv[2], sys.argv[3]), ensure_ascii=False))
    elif tipo == 'archivo': print(json.dumps(registrar('archivo', sys.argv[2], sys.argv[3], sys.argv[2]), ensure_ascii=False))
