# Terrenos con los rasgos del sector campus U. Andes / La Plaza Sur que el relieve de 30 m no resuelve (aportes de Lester, 11-oct-2026,
# Google Earth y Street View): (1) camino recto del cerro, (2) calzada baja de La Plaza Sur hacia el norte, (3) entrada principal a la
# universidad (claro → patio hundido), (4) entrada secundaria al estacionamiento. Son representantes gruesos (canales rectangulares con
# fondo descendente aguas abajo), no mediciones. Uso: python terreno_campus.py BASE SALIDA
import sys, subprocess, os, shutil
B, S = sys.argv[1], sys.argv[2]; tmp = S + '.tmp.npz'
pasos = [('trazo_camino_recto.json', 5, 0.4), ('trazo_la_plaza_sur.json', 7, 0.6), ('trazo_entrada_universidad.json', 4, 0.5), ('trazo_estacionamiento.json', 4, 0.3)]
shutil.copy(B, tmp)
for tr, ancho, prof in pasos:
    r = subprocess.run([sys.executable, 'tallar_cauce.py', tmp, tmp + '2.npz', str(ancho), str(prof), tr], capture_output=True, text=True)
    print(tr, '→', [l for l in r.stdout.splitlines() if 'tallado' in l]); os.replace(tmp + '2.npz', tmp)
os.replace(tmp, S); print('terreno', S)
