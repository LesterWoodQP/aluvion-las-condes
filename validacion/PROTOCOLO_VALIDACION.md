# Protocolo de versiones, experimentos y validación

Versión 1. Fijado el 11 de octubre de 2026, antes de cruzar el modelo con cualquier observación reservada. Este archivo solo se amplía: cada cambio se agrega como una entrada nueva, con fecha y justificación, y nunca se reescribe lo anterior. Su historial queda en git.

## 1. Versiones congeladas

- Cada PDF publicado se guarda tal como se publicó en `sitio/paper/versiones/`, con su huella en `SHA256SUMS.txt`.
- Además, cada versión tiene una etiqueta de git (`paper-vAAAA-MM-DD[letra]`, `exposicion-v…`).
- El enlace principal (`paper/aluvion-las-condes.pdf`) siempre apunta a la última versión; las anteriores no se borran ni se reemplazan.
- Los terrenos no se modifican después de usarse: cada variante tiene un archivo propio (v4_tallado, v4_adp, v4_v5qh, v4_v6, v4_v6p).
- El código queda versionado en git. `res/registro_experimentos.json` anota, para cada corrida, el commit de `sim.py` vigente.

## 2. Registro de experimentos

- `registro_experimentos.py` genera `res/registro_experimentos.json` con todas las corridas, también las que no se usan: completadas, detenidas, canceladas, fallidas y descartadas.
- Para cada corrida guarda el equipo, las fechas, los parámetros, el terreno con su huella, el commit de `sim.py`, el estado y el motivo.
- La tabla de corridas del paper (anexo) y la página Datos muestran solo las completadas. Este registro conserva el resto, con el motivo de cada detención o descarte. Por ejemplo, el borde transmisivo que creaba masa, el terreno SPOT con depresiones espurias, v20 excluida por un artefacto de umbral, el radio de captura de 12 m y v22–v24 detenidas.
- Las corridas descartadas no se borran: quedan archivadas en `res/v2_descartadas`, `res/v3_*` y `res/cancelados`.

## 3. Observaciones de ajuste y observaciones reservadas

Ser transparentes sobre qué observaciones se han visto es más importante que la pureza del diseño. Todas las del grupo A se usaron, directa o indirectamente, para formular, comparar o seleccionar hipótesis. Por eso el índice exploratorio de compatibilidad (IEC) **no es una validación**.

### A. Observaciones de ajuste (usadas para formular y seleccionar)

| Observación | Uso |
|---|---|
| Calles con barro informadas (Senapred y prensa) | Componente «calles» del IEC |
| Recintos afectados: Clínica UC Christus, Duoc UC, Clínica U. de los Andes, campus U. de los Andes | Componente «sitios» del IEC |
| Alcance hasta Av. Padre Hurtado | Componente «alcance»; fijó el volumen de ~300 mil m³ |
| Perímetro de prensa (hasta el 10-oct) y zona afectada oficial de IDE Chile (desde el 11-oct) | Componente «perímetro» del IEC |
| Cerca de 1 m en la urgencia de la Clínica UC Christus | Contraste de profundidad usado al comparar terrenos |
| Desborde informado en Francisco Bulnes Correa y continuidad cartográfica por Quebrada Honda | Diseño de los escenarios del colector |
| Relatos del vicerrector, Carabineros y el video de Quinta Conectado sobre el campus | Formulación de las hipótesis del brazo sur y de la cuenca local de la Biblioteca |

### B. Observaciones ya consultadas, no usadas en el IEC ni en la selección

Su contraste es solo descriptivo. No son independientes, porque se cruzaron con todas las corridas el 11-oct (`validacion/cruce_ide_20261011.json`) y sus resultados se conocieron mientras se diseñaban corridas posteriores.

| Observación | Uso |
|---|---|
| 2.266 predios afectados de IDE Chile (solo agregado) | Cruce descriptivo |
| 368 tramos de ejes viales afectados de IDE Chile | Cruce descriptivo |
| Balances de viviendas afectadas, con daño mayor e inhabitables | Contraste descriptivo en el subestudio de exposición |

### C. Observaciones reservadas (para probar, no para ajustar)

1. **Equipamiento afectado de IDE Chile.** Son 51 puntos (`fuentes/visor_bbnn/equipamiento_afectado.geojson`, SHA-256 `1690627d…f50e821c`, registro probatorio 11-oct 10:17 UTC). Se descargó, pero nunca se cruzó con el modelo. Se excluyen 2 puntos que coinciden con recintos de ajuste (Pontificia Universidad Católica de Chile = Clínica UC Christus, y Duoc), y quedan 49.
   - **Límite.** Los puntos están dentro de la zona oficial, que ya se usó en el IEC. Por eso la prueba es solo parcialmente independiente: comparte información espacial con el ajuste.
2. **Imágenes Sentinel-1 posteriores al evento.** Cambio de retrodispersión y de coherencia. Aún no se han descargado. La métrica se fijará en este archivo antes de descargarlas.
3. **Fuentes oficiales o técnicas futuras** que entreguen marcas de nivel, espesores de depósito o el informe de Sernageomin. Se reservan desde que se conozcan, y su métrica se fija aquí antes de cruzarlas.

## 4. Prueba con el equipamiento reservado (definida antes de mirar resultados)

- **Métrica principal: sensibilidad.** Es la fracción de los 49 puntos que tienen al menos una celda con espesor máximo mayor que 5 cm a 15 m o menos. Los edificios son bloques en el modelo, por lo que el barro se evalúa en la calle o el antejardín contiguo; 15 m es el orden de la mitad de una manzana.
- **Sin falsos positivos.** La capa solo contiene equipamientos afectados, así que no permite medirlos. Esa limitación se informa explícitamente.
- **Referencias.** La sensibilidad del candidato se compara con la de dos referencias calculadas en la misma ejecución: v01 (solo el cauce principal) y e03 (solo el desborde en la embocadura).
- **Criterio, fijado de antemano.** La prueba se considera favorable si el candidato alcanza una sensibilidad de al menos 0,70 y supera a ambas referencias. Si no se cumple, se informa como desfavorable y no se ajusta el modelo para aprobarla.
- **Candidato.** Se selecciona **solo con las observaciones de ajuste (A)**: el mayor IEC entre las corridas completadas cuando terminen v25–v29. Luego se congela con `validacion/reserva/prueba_reservada.py congelar <candidato> v01 e03`, que guarda la huella de los resultados y el commit del código.
- **Ejecución única.** La prueba se ejecuta una vez (`… probar`). Toda ejecución queda anotada en `validacion/reserva/ejecuciones.jsonl` (solo agregar) y se informa, sea cual sea su resultado.
- **Después de la prueba.** Si más adelante se cambia el modelo, la capa de equipamiento pasa al grupo B, y una nueva prueba requiere otra observación reservada.

## 5. Cómo se informa

Los resultados del paper, el sitio y la página Simulaciones se clasifican así:

- **ajuste** (grupo A: compatibilidad, no validación);
- **contraste descriptivo** (grupo B);
- **prueba con observaciones reservadas** (grupo C).

La validación científica independiente sigue pendiente, aunque la prueba del grupo C resulte favorable.

## Enmienda 1 (11-oct-2026, escrita después de evaluar v25 y v29 y antes de evaluar v27 y v28)

**Qué se sabía al escribirla.** v25 y v29 obtienen un IEC de 78, pero en ambas el componente «sitios» llega a 1,00 solo por el punto de control del campus: 0,10 m en v25 y 0,15 m en v29, ambas con paso normal. Es el mismo patrón por el que se excluyó v20, cuya repetición con paso fino (v19) bajó a 0,01 m. Esta enmienda se escribe conociendo esos resultados y se declara así.

**Regla de selección, que completa la sección 4:**
1. Un IEC que depende de un único punto de control y no se repitió con paso fino se reemplaza por su IEC sin ese punto (el componente «sitios» se calcula con los otros tres recintos).
2. Las diferencias de IEC menores que 3 puntos se consideran empates, porque no son evidencia concluyente de superioridad (lo mismo que dicen el sitio y el paper).
3. En caso de empate se elige la configuración verificada con paso fino.

**Consecuencia hoy.** z02, v25 y v29 empatan en 72. El candidato es **z02**, salvo que v27 o v28 superen 75 con la regla 1.

**Prueba adicional de v29.** Se lanza z29: v29 con paso fino (CFL 0,5). Si z29 mantiene el barro en el campus (h > 5 cm), v29 pasaría a 78 verificado. Eso **no cambia el candidato ya congelado para la prueba reservada**, que se ejecuta una sola vez; se informaría como resultado posterior, con las observaciones reservadas ya consumidas.

## Resultado de la prueba con el equipamiento reservado (ejecución única, 11-oct-2026)

- **Orden de los pasos, verificable en git:**
  1. enmienda 1 (commit 52c944e);
  2. candidato congelado (eb9adea);
  3. prueba ejecutada y resultado commiteado de inmediato.
- **Resultado:**

| Corrida | Rol | Sensibilidad | Equipamientos alcanzados |
|---|---|---|---|
| z02 | candidato | 0,388 | 19 de 49 |
| v01 | referencia | 0,388 | 19 de 49 |
| e03 | referencia | 0,000 | 0 de 49 |

- **Veredicto según el criterio prefijado: DESFAVORABLE.** No alcanza 0,70 y no supera a v01. El modelo no se ajusta para aprobarla. Desde ahora, la capa de equipamiento pasa al grupo B (contraste descriptivo).
- **Diagnóstico posterior.** No cambia el veredicto y se informa como exploratorio:
  - 48 de los 49 puntos están dentro de la zona oficial y todos dentro del dominio del modelo;
  - la distancia mediana a la celda simulada con barro más cercana es de 32 m;
  - 24 puntos quedan a 30 m o menos, 30 a 50 m o menos y 16 a más de 100 m;
  - los más lejanos están en sectores de la zona oficial que el modelo no moja; varios son instalaciones de servicio (compañía de agua, juntas de vecinos, recintos municipales), cuya afectación pudo deberse a causas distintas del barro (servicio, acceso);
  - el resultado concuerda con el contraste descriptivo: z02 moja solo cerca del 20 % del área de la zona oficial y el 30 % de los predios afectados.
- **Lectura.** Además de extenderse fuera de la zona oficial, el modelo deja sin barro partes importantes de ella. La prueba no refuta las hipótesis de origen, pero muestra que la reconstrucción actual no reproduce la distribución espacial de la afectación oficial. Explicaciones posibles, sin evaluar: la resolución del terreno, la representación de los edificios como bloques, el volumen o su reparto en el tiempo, aportes locales no modelados y criterios de afectación oficial distintos del espesor de barro.

## Corrección 1 (11-oct-2026, tarde)

En el diagnóstico posterior de la prueba reservada dice «el 30 % de los predios afectados». La cifra exacta es 717 de 2.266, es decir 31,6 % (≈32 %). La corrección no cambia el veredicto ni la métrica de la prueba. La detectó la revisión automatizada de la traducción al inglés.

## Nota 2 (11-oct-2026, 18:40): resultado posterior a la prueba

v26 (casas porosas) terminó después de que se congeló el candidato y se ejecutó la prueba. Por la regla 1 su IEC es 76, cuatro puntos sobre z02, y en la capa de equipamiento llega a 37 de 49 puntos (0,755). Esa capa ya pasó al grupo B, así que ese valor es un contraste descriptivo y no cambia el resultado de la prueba única, que sigue siendo desfavorable para z02. Si v26 o su repetición con paso fino (z26) pasa a ser la hipótesis seleccionada, su prueba requerirá observaciones reservadas nuevas, fijadas aquí antes de cruzarlas.

## Nota 3 (12-oct-2026, 00:40): z29

z29 (v29 con paso fino) mantiene el punto del campus sobre 5 cm (0,09 m), así que su IEC de 78 queda verificado con paso fino según la regla 1. Igual que v26, es posterior a la prueba única y no la modifica. Cualquier nueva selección (z29, z26 o v31) requerirá observaciones reservadas nuevas, fijadas aquí antes de cruzarlas.

## Nota 4 (12-oct-2026, 09:30): z32

z32 (v32 con paso fino) da un IEC de 82, verificado. Igual que v26 y z29, es posterior a la prueba única. Si la hipótesis integrada pasa a ser la seleccionada, su prueba requerirá observaciones reservadas nuevas (por ejemplo Sentinel-1, o marcas de nivel o espesores oficiales futuros), con la métrica fijada aquí antes de cruzarlas.
