# Preguntas abiertas: por dónde seguir

El estudio se cerró el 13 de octubre de 2026 con 84 simulaciones. Esta lista resume lo que **quedó sin probar** y qué haría falta para avanzar. Sirve como punto de partida para quien quiera continuar, contrastar o refutar los resultados.

## 1. Validación con observaciones independientes

- **Estado:** la única prueba con observaciones reservadas, definida antes de mirar resultados, fue desfavorable: 19 de 49 equipamientos (`validacion/reserva/`). Todo lo posterior, incluida la hipótesis integrada (IEC 79–82), es ajuste.
- **Qué falta:** observaciones nuevas no usadas para construir las hipótesis:
  - imágenes de radar Sentinel-1 posteriores al evento (cambio de retrodispersión en el barro);
  - marcas de nivel o espesores medidos en terreno;
  - una cartografía oficial de espesores.
- **Cómo seguir:** congelar un candidato con `validacion/reserva/prueba_reservada.py` sobre un conjunto nuevo y ejecutarlo una sola vez, según `validacion/PROTOCOLO_VALIDACION.md`.

## 2. Lluvia dentro de la cuenca

- **Estado:** no hay pluviómetro dentro de la cuenca. Se usó la estación DGA Río Molina, a unos 7 km (`fuentes/hietograma_rio_molina_20261008.csv`, digitalizada de una figura del CR2), con un desfase supuesto entre la lluvia y el pico del hidrograma.
- **Qué falta:** registros de mayor resolución temporal, radar meteorológico o estaciones más cercanas, y la serie original de la DGA.

## 3. Volumen, composición y reología del flujo

- **Estado:** el volumen (~300 mil m³ de mezcla) es el que exige el modelo para alcanzar Padre Hurtado, y coincide en orden con un balance de lluvia con suelo saturado. La concentración y la reología se tomaron de tablas publicadas (FLO-2D, Glenwood 2).
- **Qué falta:** mediciones del depósito (espesores, granulometría, concentración) y ensayos reológicos del material.

## 4. Obras de drenaje

- **Estado:** el colector de Francisco Bulnes Correa se representó como un sumidero de **capacidad supuesta**. Los escenarios no evalúan la obra real.
- **Qué falta:** capacidad de diseño, sección, pendiente y estado real del colector y de los ductos, a partir de información de diseño e inspección.

## 5. Clínica UC Christus

- **Estado:** ninguna configuración reproduce a la vez el espesor cercano a 1 m informado y la extensión dentro de la zona afectada oficial. Cuando las casas retienen barro, el espesor calculado allí baja a ~0,3 m.
- **Qué falta:** una representación de los lotes y cierres más fiel que «casas porosas», o un relieve de mayor resolución en ese sector.

## 6. Relieve

- **Estado:** el terreno base es FABDEM de 30 m remuestreado a 4 m. Calzadas, soleras y pasos estrechos se tallaron a partir de trazados de Google Earth y Street View, como representaciones gruesas. Un video publicado por Meganoticias a las 18:16 del 8 de octubre muestra agua turbia que baja del bosque y llena un patio hundido junto a un edificio del campus de la Universidad de los Andes, con unos 15–35 cm según la altura de las bancas (ubicación en `validacion/patio_video.json`). Con la malla de la ciudad, el modelo deja ese patio casi seco (~6 cm); con malla fina en el campus (m36), llega a 0,17 m, dentro de ese rango: la resolución importa.
- **Qué falta:** un relieve LiDAR del sector y su efecto sobre las calles y el campus.

## 7. Procesos que el modelo no simula

- Erosión y depósito durante el recorrido, y cambios de concentración del flujo.
- Troncos y vehículos arrastrados, y obstrucciones dinámicas.
- Drenaje urbano (sumideros) e infiltración dentro de la ciudad.

## 8. Incendio

- **Estado:** la severidad se estimó con dNBR de Sentinel-2: 82 % de las cuencas con señal de quema y 10 % con severidad moderada-alta o alta (`validacion/incendio/`). Los incrementos de escorrentía por severidad son supuestos. Los modelos de volumen (Gartner et al., 2014) y de probabilidad (Staley et al., 2017) se calibraron fuera de Chile.
- **Qué falta:**
  - umbrales de severidad calibrados en matorral esclerófilo;
  - mediciones de hidrofobicidad;
  - un modelo de erosión posincendio.

## 9. Obstáculo de troncos

- **Estado:** se ensayó una sola ubicación y una altura supuesta de 3 m al final de la línea de árboles. En el modelo, el obstáculo no desvía el flujo hacia el sur.
- **Qué falta:** verificación en terreno de la ubicación y del volumen de material leñoso.

## Cómo empezar

1. Leer el informe (`paper/aluvion-las-condes.pdf`; en inglés, `paper/en/`), en especial las secciones «Las hipótesis, una por una» y «Conclusiones y cierre del estudio».
2. Revisar `res/registro_experimentos.json` y `res/corridas.csv` para ver qué se probó y con qué resultado.
3. Reconstruir el terreno (`extraccion/`, `prep_v4.py`) y repetir una simulación de referencia (ver `README.md`).
