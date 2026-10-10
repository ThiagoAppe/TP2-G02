SELECT
    i.inventario_id AS id,
    i.pelicula_id AS pelicula,
    i.tienda_id AS tienda,
    a.alquiler_id AS alquiler,
    a.fecha_alquiler AS fecha,
    a.fecha_devolucion AS devolucion
FROM inventario AS i
LEFT JOIN alquiler AS a
    ON i.inventario_id = a.inventario_id;