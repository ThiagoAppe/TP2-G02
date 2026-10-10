SELECT
    p.pelicula_id AS pelicula,
    p.titulo AS titulo
FROM pelicula AS p
WHERE NOT EXISTS (
    SELECT 1
    FROM inventario AS i
    WHERE i.pelicula_id = p.pelicula_id
)
ORDER BY p.pelicula_id;
