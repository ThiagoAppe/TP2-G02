/*
Construye el conjunto de trabajo crudo para la comparación SQL–pandas.

Se parte de inventario para conservar cada copia física. El LEFT JOIN mantiene
las copias que todavía no tienen alquileres, por lo que alquiler, fecha y
devolucion pueden ser NULL en esos casos.
Cada fila representa una copia y, si existe, uno de sus alquileres.
*/
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
