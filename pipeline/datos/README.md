# Metas operativas por tienda

`metas_rotacion_tienda.csv` es el segundo origen del pipeline de la Actividad 4. No proviene de Sakila: contiene parámetros operativos definidos para este trabajo y se combina con las métricas observadas por `tienda_id`.

| Campo | Tipo esperado | Regla | Decisión adoptada |
| --- | --- | --- | --- |
| `tienda_id` | entero | Único y presente en SQL Server. | Se incluyen las tiendas 1 y 2, las dos presentes en el inventario analizado. |
| `meta_rotacion` | decimal positivo | Objetivo mínimo de alquileres por copia en el período observado. | `3.50` para ambas tiendas. Es una referencia común de eficiencia, no una predicción de demanda ni un valor calculado por el pipeline. |
| `umbral_ocio_dias` | entero positivo | Días promedio de ociosidad desde los cuales una combinación se revisa. | `30` días para ambas tiendas: una referencia operativa de un mes calendario. |

Usar los mismos umbrales para las dos tiendas evita que el archivo favorezca artificialmente a una de ellas. Si el equipo o el negocio define una política distinta, se modifican sólo los valores del CSV y se deja asentada la razón de ese cambio aquí; no se modifica el código del ETL.

## Contrato que validará el pipeline

Antes de hacer el `merge`, el pipeline deberá comprobar que:

1. El archivo tiene exactamente las columnas `tienda_id`, `meta_rotacion` y `umbral_ocio_dias`.
2. No hay valores nulos ni tiendas repetidas.
3. Las tres columnas son numéricas; `tienda_id` y `umbral_ocio_dias` son enteros, y los umbrales son mayores que cero.
4. El conjunto de tiendas coincide con el que se extrae de SQL Server.

El cruce se realizará como `left merge` desde las métricas por película y tienda hacia este archivo, con `validate="many_to_one"`. La ausencia de una meta debe detener el proceso antes de la carga a `TP2_RotacionInventario`.
