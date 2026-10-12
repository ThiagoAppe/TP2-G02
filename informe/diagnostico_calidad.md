# Actividad 2 — Diagnóstico de calidad de datos

## Objetivo y reconocimiento inicial

Se evaluó el conjunto para analizar la rotación del inventario por tienda. Tiene **16.045 filas** y **6 columnas**: `id`, `pelicula`, `tienda`, `alquiler`, `fecha` y `devolucion`. La cantidad de filas es coherente con las 16.044 filas de alquiler y una copia de inventario sin alquiler asociado.

La revisión de primeras filas, muestra aleatoria, `info()` y `describe()` con percentiles adicionales no mostró identificadores ni fechas mal interpretados. `id`, `pelicula` y `tienda` son enteros; `fecha` y `devolucion` son fecha/hora. `alquiler` aparece como `float64` únicamente porque contiene un nulo; se conserva así en el conjunto crudo para no ocultar ese caso.

## Diagnóstico y decisiones

| Control | Resultado | Decisión y fundamento |
| --- | --- | --- |
| Valores faltantes | `alquiler` y `fecha`: 1 (0,01 %) cada uno; `devolucion`: 184 (1,15 %). | Conservarlos. El primer caso es la copia nunca alquilada; las devoluciones faltantes representan alquileres abiertos. Se excluyen solo de cálculos que requieren devolución. |
| Duplicados | 0 grupos duplicados por `alquiler` y por `id` + `alquiler`. | No aplicar transformación. |
| Reglas de negocio | 0 devoluciones anteriores al alquiler; 0 alquileres sin copia, película o tienda; 0 copias con película o tienda inconsistente. | No aplicar transformación. |
| Variables categóricas | No hay categorías textuales. Las tiendas presentes son `1` y `2`. | No normalizar; los identificadores son consistentes. |
| Columnas constantes | Ninguna. | Conservar todas las columnas. |
| Cobertura temporal | Alquileres: 24/05/2005 a 14/02/2006. Devoluciones: 25/05/2005 a 02/09/2005. Hay 182 alquileres posteriores a la última devolución registrada. | Conservar los registros, pero declarar la cobertura incompleta de devoluciones como limitación para interpretar ociosidad y duración. |

## Valores atípicos

Se aplicó IQR al **índice de rotación**, la métrica principal de la variante, calculado por película y tienda.

| Q1 | Q3 | IQR | Límites | Atípicos |
| ---: | ---: | ---: | --- | ---: |
| 3,00 | 4,00 | 1,00 | 1,50 a 5,50 | 0 |

No se detectaron valores atípicos. Por lo tanto, no se descartan ni corrigen filas por este criterio.

## Control específico de la variante

| Control | Resultado | Decisión y fundamento |
| --- | ---: | --- |
| Copias de inventario nunca alquiladas | 1 | Conservar e informar: es inventario inmovilizado, no un error de carga. |
| Películas del catálogo sin copias | 42 | Conservar e informar: no pueden tener rotación porque no existe stock. Son una limitación del análisis de inventario, no una película con baja demanda. |

## Contraste pandas y T-SQL

Los controles replicados coinciden entre ambas herramientas.

| Control | pandas | T-SQL |
| --- | ---: | ---: |
| Alquileres, fechas de alquiler y devoluciones faltantes | 1, 1, 184 | 1, 1, 184 |
| Grupos de alquiler duplicados | 0 | 0 |
| Copias nunca alquiladas | 1 | 1 |
| Películas sin copias | 42 | 42 |

## Conclusión

El conjunto es confiable para calcular la rotación de las copias que existen en inventario: no presenta duplicados, incumplimientos de reglas ni rotaciones atípicas. Los faltantes no se tratan como errores porque describen casos reales del dominio. Sin embargo, la cobertura de devoluciones es incompleta respecto de los alquileres; por ello, los resultados de ociosidad deben interpretarse solo para alquileres con devolución registrada y no permiten generalizar el comportamiento temporal a todo el período observado.
