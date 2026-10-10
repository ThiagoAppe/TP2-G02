/*
Tabla destino del ETL de la Actividad 1, Variante 2.
Una fila representa el estado calculado para una pelicula en una tienda.
La clave primaria permite realizar una carga tipo upsert en futuras ejecuciones.
*/
IF OBJECT_ID('dbo.TP2_RotacionInventario', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.TP2_RotacionInventario (
        pelicula_id                INT             NOT NULL,
        titulo                     NVARCHAR(255)   NOT NULL,
        tienda_id                  INT             NOT NULL,
        cantidad_copias            INT             NOT NULL,
        cantidad_alquileres        INT             NOT NULL,
        indice_rotacion            DECIMAL(28, 12) NOT NULL,
        promedio_dias_ociosidad    DECIMAL(28, 12) NULL,
        fecha_carga                DATETIME2(0)    NOT NULL
            CONSTRAINT DF_TP2_RotacionInventario_fecha_carga DEFAULT SYSDATETIME(),

        CONSTRAINT PK_TP2_RotacionInventario
            PRIMARY KEY (pelicula_id, tienda_id),
        CONSTRAINT CK_TP2_RotacionInventario_copias
            CHECK (cantidad_copias > 0),
        CONSTRAINT CK_TP2_RotacionInventario_alquileres
            CHECK (cantidad_alquileres >= 0),
        CONSTRAINT CK_TP2_RotacionInventario_rotacion
            CHECK (indice_rotacion >= 0)
    );
END;
