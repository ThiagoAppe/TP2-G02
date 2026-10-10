SELECT
    i.inventario_id AS id,
    i.pelicula_id AS pelicula,
    i.tienda_id AS tienda
FROM inventario AS i
WHERE NOT EXISTS (
    SELECT 1
    FROM alquiler AS a
    WHERE a.inventario_id = i.inventario_id
)
ORDER BY i.inventario_id;
