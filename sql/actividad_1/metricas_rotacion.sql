WITH alquileres_con_anterior AS (
    SELECT
        i.inventario_id AS id,
        i.pelicula_id AS pelicula,
        i.tienda_id AS tienda,
        a.alquiler_id AS alquiler,
        a.fecha_alquiler AS fecha,
        a.fecha_devolucion AS devolucion,
        LAG(a.fecha_devolucion) OVER (
            PARTITION BY i.inventario_id
            ORDER BY a.fecha_alquiler
        ) AS devolucion_anterior
    FROM inventario AS i
    LEFT JOIN alquiler AS a
        ON i.inventario_id = a.inventario_id
),
ociosidad AS (
    SELECT
        *,
        DATEDIFF(DAY, devolucion_anterior, fecha) AS dias_ociosidad
    FROM alquileres_con_anterior
)
SELECT
    pelicula,
    tienda,
    COUNT(DISTINCT id) AS cantidad_copias,
    COUNT(alquiler) AS cantidad_alquileres,
    CAST(COUNT(alquiler) AS DECIMAL(28, 12))
        / CAST(COUNT(DISTINCT id) AS DECIMAL(28, 12)) AS indice_rotacion,
    AVG(CAST(dias_ociosidad AS DECIMAL(28, 12))) AS promedio_dias_ociosidad
FROM ociosidad
GROUP BY
    pelicula,
    tienda
ORDER BY
    pelicula,
    tienda;
