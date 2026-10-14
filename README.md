# Aluvión de San Carlos de Apoquindo (Las Condes, 8 de octubre de 2026): modelo y datos para investigar

Este repositorio reúne el modelo, los datos derivados y el informe de un estudio técnico independiente que reconstruyó con un modelo bidimensional de aguas someras con reología de barro (ANUGA 4.0.1 con la ley cuadrática de O'Brien y Julien) el flujo de barro del 8 de octubre de 2026 en San Carlos de Apoquindo, Las Condes, Santiago de Chile.

Está pensado como **punto de partida para otros investigadores**: qué se hizo, con qué datos, cómo repetirlo y qué quedó sin probar (ver [`PREGUNTAS_ABIERTAS.md`](PREGUNTAS_ABIERTAS.md)). La presentación pública del estudio, con un visor 3D, está en https://aluvion.hirely.cl.

## Naturaleza y alcance

- Ejercicio técnico **independiente y de carácter académico**, sin carácter oficial. No es un peritaje.
- Los resultados son **respuestas de un modelo a parámetros de entrada declarados**, varios de ellos supuestos. Ninguna cifra calculada es una medición.
- **No se afirma la causa del evento ni se atribuyen responsabilidades.** Los escenarios del colector de Francisco Bulnes Correa usan capacidades supuestas y no describen la obra real, cuya capacidad, sección y estado no son públicos.
- Los hechos provienen de información pública, citada y atribuida, con un registro de consultas fechado (`fuentes/registro_consultas.jsonl`).
- El estudio se **cerró el 13 de octubre de 2026**. La sección «Conclusiones y cierre del estudio» del informe resume hacia dónde apuntan los resultados y qué queda abierto.

## Qué hay aquí

| Ruta | Contenido |
|---|---|
| `sim.py` | El modelo: ANUGA + reología de barro, hidrogramas por cauce, lluvia constante u hietograma, colector como sumidero de capacidad supuesta, malla refinada |
| `prep_v4.py`, `cuenca.py`, `extraccion/` | Construcción del terreno y de las cuencas a partir de datos públicos (FABDEM, Overture Maps, OpenStreetMap) |
| `tallar_cauce.py`, `terreno_campus.py`, `terreno_tapon.py`, `trazo_*.json` | Rasgos que el relieve de 30 m no resuelve, tallados a partir de trazados |
| `calibrar.py`, `evaluar_iec.py`, `ajuste_escenarios.py`, `evaluar_campus.py`, `evaluar_micro.py` | Comparación de cada simulación con lo observado y el índice exploratorio de compatibilidad (IEC) |
| `volumen_previo.py`, `validacion/incendio/` | Volumen por balance lluvia–escorrentía, severidad del incendio con Sentinel-2 y escenarios sin incendio |
| `verif_parada.py`, `verif_conv2.py` | Verificaciones numéricas de la reología y de la convergencia |
| `validacion/` | Protocolo de validación, prueba con observaciones reservadas y bitácoras de cada ronda |
| `res/` | Métricas de todas las simulaciones y registro de experimentos, incluidos los descartados |
| `fuentes/` | Registro probatorio de fuentes, lluvia de la estación Río Molina y datos meteorológicos |
| `paper/` | Informe en LaTeX y PDF, en español y en inglés (`paper/en/`), y sub-estudio de exposición censal |

Cada archivo tiene en su historial un commit con su descripción, y cada carpeta tiene un `README.md`.

## Reproducir una simulación

Requisitos: Python 3.12 y las dependencias de `requirements.txt`. Primero se construye el terreno con `extraccion/` y `prep_v4.py`; los terrenos y los resultados binarios no se incluyen por tamaño. Ejemplo, la hipótesis integrada con la lluvia medida (corrida p34b):

```bash
python sim.py --origen H3 --cv 0.40 --cv_faldeo 0.10 \
  --hietograma fuentes/hietograma_rio_molina_20261008.csv --t0_fuentes 10200 \
  --lluvia_neta --lluvia_faldeo --vol 300000 --qp 250 --suelo glenwood2b \
  --cfl 1.0 --fino 30 --terreno terreno_v4_v6pc.npz --salida res/p34b
python evaluar_iec.py p34b
```

Cada simulación de la ciudad completa tarda entre 5 y 14 horas en un núcleo. Los parámetros de las demás simulaciones están en `res/registro_experimentos.json` y en el catálogo del informe.

## Qué no se incluye

- Terrenos y resultados binarios (`*.npz`, unos 60 GB), que se regeneran con los scripts.
- Capturas de páginas de prensa (derechos de terceros); el registro conserva URL, fecha, dato usado y huella.
- Capas descargadas del visor de emergencia de Bienes Nacionales / IDE Chile; los cruces se publican solo en forma agregada.
- El sitio web, el visor 3D y sus scripts de mantención.

## Licencias

- Código (programas y scripts): [GNU GPL v3.0](https://www.gnu.org/licenses/gpl-3.0.html), texto en `LICENSE-GPL-3.0`.
- Textos, figuras, tablas y datos derivados: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), texto en `LICENSE-CC-BY-NC-SA-4.0`.
- El resumen de qué licencia aplica a cada tipo de archivo está en `LICENSE`.
- Datos de terceros, con sus propias condiciones: FABDEM (CC BY-NC-SA 4.0), Copernicus GLO-30 y Sentinel-2 (datos Copernicus), OpenStreetMap y Overture Maps (ODbL), SPOT 2014 vía OpenTopography (CC BY 4.0), Censo 2017 (INE), Open-Meteo (CC BY 4.0).

## Citar

Wood, L. (2026). *Reconstrucción numérica independiente del aluvión de San Carlos de Apoquindo (Las Condes, 8 de octubre de 2026)*. https://aluvion.hirely.cl · https://github.com/LesterWoodQP/aluvion-las-condes

## Uso de herramientas de IA

El estudio se desarrolló con asistencia de herramientas de inteligencia artificial (Claude Code de Anthropic y Codex de OpenAI) para programación, redacción, traducción y revisión, bajo dirección y revisión del autor. El informe incluye una declaración detallada.
