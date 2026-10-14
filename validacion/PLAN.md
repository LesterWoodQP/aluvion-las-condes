# Validación independiente con imágenes satelitales (definida el 9-oct-2026, ANTES de ver las imágenes posteriores)

Principio: estas observaciones NO se usan para calibrar ni para elegir hipótesis. Se comparan una sola vez contra las
simulaciones ya aceptadas/seleccionadas con la evidencia de prensa, para estimar la capacidad predictiva del modelo.

## Escenas
- Sentinel-1 RTC (radar, corregido por terreno; Planetary Computer `sentinel-1-rtc`), órbita relativa 83 descendente 09:55 UTC:
  previas 2026-09-21, 09-27, 10-03 (compuesto medio para reducir moteado); posterior 2026-10-09 (disponible en GRD; RTC pendiente).
  Control: par previo 09-27 vs 10-03 (sin evento) para estimar la tasa de cambio espurio.
- Sentinel-2 L2A (óptico, 10 m): previa útil 2026-09-21 (76 % nubes, revisar nubes locales); posteriores cuando haya escena con
  el área despejada (pasadas cada ~5 días: 9, 14, 19 oct...).
- Búsquedas archivadas en `validacion/stac/` y en `fuentes/registro_consultas.jsonl` (script `validacion/satelite_buscar.py`).

## Método fijado de antemano
1. Radar: razón logarítmica r = 10·log10(σ⁰_post / media(σ⁰_pre)) en VV y VH, filtro de moteado 3×3; cambio si |r| supera el
   percentil 99 del par de control. Máscara de sombras/layover y de edificios altos.
2. Óptico: índice de barro/sedimento (rojo/verde, SWIR/NIR) post − pre; umbral de Otsu; máscara de nubes SCL.
3. Métricas contra el modelo: IoU (Jaccard), precisión y sensibilidad por área; acierto por calle (fracción de puntos de control);
   todo con la envolvente de simulaciones aceptables y con la mejor simulación por separado.
4. Se reportará también lo que la imagen NO puede ver (calles de < 10 m, lodo delgado, limpieza antes de la pasada).
