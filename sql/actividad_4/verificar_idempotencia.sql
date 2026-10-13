/*
Evidencia de idempotencia de la Actividad 4.

Después de cada ejecución del pipeline, filas_destino debe coincidir con
claves_pelicula_tienda. Al ejecutar dos veces con las mismas fuentes, ambos
conteos deben mantenerse idénticos.
*/
SELECT
    COUNT(*) AS filas_destino,
    COUNT(DISTINCT CONCAT(
        CAST(pelicula_id AS varchar(11)),
        ':',
        CAST(tienda_id AS varchar(11))
    )) AS claves_pelicula_tienda
FROM dbo.TP2_RotacionInventario;
