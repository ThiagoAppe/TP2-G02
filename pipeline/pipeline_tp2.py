"""Pipeline ETL de rotación de inventario por tienda.

Extrae datos desde SQL Server y un CSV de metas, calcula las métricas en forma
vectorizada y reemplaza de manera idempotente la tabla destino. Se ejecuta con
``venv_tp2/bin/python pipeline/pipeline_tp2.py`` desde la raíz del proyecto.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Collection, Sequence
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    select,
    text,
)
from sqlalchemy.engine import Connection, Engine

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from config_conexion import get_engine
from esquema import SCHEMA

LOGGER = logging.getLogger(__name__)
RUTA_METAS_PREDETERMINADA = (
    Path(__file__).resolve().parent / "datos" / "metas_rotacion_tienda.csv"
)
RUTA_LOG = Path(__file__).resolve().parent / "logs" / "pipeline_tp2.log"

ESQUEMA_DESTINO = "dbo"
TABLA_DESTINO = "TP2_RotacionInventario"
COLUMNAS_METAS = ["tienda_id", "meta_rotacion", "umbral_ocio_dias"]
COLUMNAS_CRUDAS = [
    "inventario_id",
    "pelicula_id",
    "titulo_pelicula",
    "tienda_id",
    "alquiler_id",
    "fecha_alquiler",
    "fecha_devolucion",
]
COLUMNAS_DESTINO = [
    "pelicula_id",
    "titulo_pelicula",
    "tienda_id",
    "cantidad_copias",
    "cantidad_alquileres",
    "indice_rotacion",
    "promedio_dias_ociosidad",
    "meta_rotacion",
    "umbral_ocio_dias",
    "cumple_meta_rotacion",
    "requiere_revision_ocio",
]

DEFINICION_TABLA_DESTINO = text("""
    IF NOT EXISTS (
        SELECT 1
        FROM sys.tables AS tabla
        INNER JOIN sys.schemas AS esquema
            ON esquema.schema_id = tabla.schema_id
        WHERE esquema.name = :esquema_destino
          AND tabla.name = :tabla_destino
    )
    BEGIN
        CREATE TABLE [dbo].[TP2_RotacionInventario] (
            [pelicula_id] INT NOT NULL,
            [titulo_pelicula] NVARCHAR(255) NOT NULL,
            [tienda_id] INT NOT NULL,
            [cantidad_copias] INT NOT NULL,
            [cantidad_alquileres] INT NOT NULL,
            [indice_rotacion] DECIMAL(18, 6) NOT NULL,
            [promedio_dias_ociosidad] DECIMAL(18, 6) NULL,
            [meta_rotacion] DECIMAL(18, 6) NOT NULL,
            [umbral_ocio_dias] INT NOT NULL,
            [cumple_meta_rotacion] BIT NOT NULL,
            [requiere_revision_ocio] BIT NULL,
            CONSTRAINT [PK_TP2_RotacionInventario]
                PRIMARY KEY ([pelicula_id], [tienda_id])
        );
    END;
    """)

CONSULTA_COLUMNAS_DESTINO = text("""
    SELECT
        COLUMN_NAME AS nombre,
        DATA_TYPE AS tipo,
        IS_NULLABLE AS admite_nulos
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = :esquema_destino
      AND TABLE_NAME = :tabla_destino;
    """)

CONSULTA_CLAVE_PRIMARIA_DESTINO = text("""
    SELECT columna.name AS nombre
    FROM sys.key_constraints AS restriccion
    INNER JOIN sys.tables AS tabla
        ON tabla.object_id = restriccion.parent_object_id
    INNER JOIN sys.schemas AS esquema
        ON esquema.schema_id = tabla.schema_id
    INNER JOIN sys.index_columns AS indice
        ON indice.object_id = tabla.object_id
       AND indice.index_id = restriccion.unique_index_id
    INNER JOIN sys.columns AS columna
        ON columna.object_id = tabla.object_id
       AND columna.column_id = indice.column_id
    WHERE esquema.name = :esquema_destino
      AND tabla.name = :tabla_destino
      AND restriccion.type = 'PK'
    ORDER BY indice.key_ordinal;
    """)

TIPOS_DESTINO_ESPERADOS = {
    "pelicula_id": ("int", "NO"),
    "titulo_pelicula": ("nvarchar", "NO"),
    "tienda_id": ("int", "NO"),
    "cantidad_copias": ("int", "NO"),
    "cantidad_alquileres": ("int", "NO"),
    "indice_rotacion": ("decimal", "NO"),
    "promedio_dias_ociosidad": ("decimal", "YES"),
    "meta_rotacion": ("decimal", "NO"),
    "umbral_ocio_dias": ("int", "NO"),
    "cumple_meta_rotacion": ("bit", "NO"),
    "requiere_revision_ocio": ("bit", "YES"),
}

TIPOS_CARGA_DESTINO = {
    "pelicula_id": Integer(),
    "titulo_pelicula": String(255),
    "tienda_id": Integer(),
    "cantidad_copias": Integer(),
    "cantidad_alquileres": Integer(),
    "indice_rotacion": Numeric(18, 6),
    "promedio_dias_ociosidad": Numeric(18, 6),
    "meta_rotacion": Numeric(18, 6),
    "umbral_ocio_dias": Integer(),
    "cumple_meta_rotacion": Boolean(),
    "requiere_revision_ocio": Boolean(),
}

CONSULTA_CONTEO_DESTINO = text("SELECT COUNT(*) FROM [dbo].[TP2_RotacionInventario];")


def _nombre_tabla(entidad_canonica: str) -> str:
    """Obtiene una tabla desde el único diccionario de esquema permitido."""
    try:
        return str(SCHEMA[entidad_canonica]["tabla"])
    except KeyError as error:
        raise KeyError(
            f"No existe el mapeo de tabla para la entidad canónica {entidad_canonica!r}."
        ) from error


def _nombre_columna(entidad_canonica: str, columna_canonica: str) -> str:
    """Obtiene una columna desde el diccionario de esquema."""
    try:
        return str(SCHEMA[entidad_canonica]["columnas"][columna_canonica])
    except KeyError as error:
        raise KeyError(
            "No existe el mapeo para "
            f"{entidad_canonica}.{columna_canonica} en esquema.py."
        ) from error


def _validar_definicion_destino(conexion: Connection) -> None:
    """Comprueba que una tabla existente conserva el contrato del ETL."""
    columnas = conexion.execute(
        CONSULTA_COLUMNAS_DESTINO,
        {"esquema_destino": ESQUEMA_DESTINO, "tabla_destino": TABLA_DESTINO},
    ).mappings()
    definicion_actual = {
        fila["nombre"]: (str(fila["tipo"]).lower(), fila["admite_nulos"])
        for fila in columnas
    }

    if definicion_actual != TIPOS_DESTINO_ESPERADOS:
        raise RuntimeError(
            "La tabla destino existente no coincide con el contrato esperado. "
            f"Esperado: {TIPOS_DESTINO_ESPERADOS}. Actual: {definicion_actual}."
        )

    clave_primaria = (
        conexion.execute(
            CONSULTA_CLAVE_PRIMARIA_DESTINO,
            {"esquema_destino": ESQUEMA_DESTINO, "tabla_destino": TABLA_DESTINO},
        )
        .scalars()
        .all()
    )
    if clave_primaria != ["pelicula_id", "tienda_id"]:
        raise RuntimeError(
            "La tabla destino debe tener la clave primaria compuesta "
            "(pelicula_id, tienda_id). "
            f"Clave actual: {clave_primaria}."
        )


def asegurar_tabla_destino(conexion: Connection) -> None:
    """Crea la tabla destino si falta y valida su definición si ya existía.

    La sentencia no borra ni carga datos. La posterior etapa de carga será la
    responsable de reemplazar el contenido dentro de una transacción.
    """
    parametros = {"esquema_destino": ESQUEMA_DESTINO, "tabla_destino": TABLA_DESTINO}
    conexion.execute(DEFINICION_TABLA_DESTINO, parametros)
    _validar_definicion_destino(conexion)
    LOGGER.info("Tabla destino %s.%s verificada.", ESQUEMA_DESTINO, TABLA_DESTINO)


def extraer_datos_sql(engine: Engine) -> pd.DataFrame:
    """Extrae sólo las columnas crudas necesarias para la métrica.

    La consulta se expresa con SQLAlchemy para que los nombres de tabla y
    columna provengan de ``SCHEMA``. No contiene valores interpolados: cuando
    se agreguen filtros de datos deberán recibirse por parámetros enlazados.
    """
    inventario_id = _nombre_columna("inventory", "inventory_id")
    inventario_pelicula = _nombre_columna("inventory", "film_id")
    inventario_tienda = _nombre_columna("inventory", "store_id")
    pelicula_id = _nombre_columna("film", "film_id")
    pelicula_titulo = _nombre_columna("film", "title")
    alquiler_id = _nombre_columna("rental", "rental_id")
    alquiler_inventario = _nombre_columna("rental", "inventory_id")
    alquiler_fecha = _nombre_columna("rental", "rental_date")
    alquiler_devolucion = _nombre_columna("rental", "return_date")

    # Declarar sólo las columnas utilizadas evita reflejar columnas ajenas a
    # esta actividad (por ejemplo, tipos espaciales) y mantiene el acceso
    # portable: todos los identificadores provienen de SCHEMA.
    metadata = MetaData()
    inventario = Table(
        _nombre_tabla("inventory"),
        metadata,
        Column(inventario_id, Integer()),
        Column(inventario_pelicula, Integer()),
        Column(inventario_tienda, Integer()),
    )
    pelicula = Table(
        _nombre_tabla("film"),
        metadata,
        Column(pelicula_id, Integer()),
        Column(pelicula_titulo, String(255)),
    )
    alquiler = Table(
        _nombre_tabla("rental"),
        metadata,
        Column(alquiler_id, Integer()),
        Column(alquiler_inventario, Integer()),
        Column(alquiler_fecha, DateTime()),
        Column(alquiler_devolucion, DateTime()),
    )

    consulta = select(
        inventario.c[inventario_id].label("inventario_id"),
        inventario.c[inventario_pelicula].label("pelicula_id"),
        pelicula.c[pelicula_titulo].label("titulo_pelicula"),
        inventario.c[inventario_tienda].label("tienda_id"),
        alquiler.c[alquiler_id].label("alquiler_id"),
        alquiler.c[alquiler_fecha].label("fecha_alquiler"),
        alquiler.c[alquiler_devolucion].label("fecha_devolucion"),
    ).select_from(
        inventario.join(
            pelicula,
            inventario.c[inventario_pelicula] == pelicula.c[pelicula_id],
        ).outerjoin(
            alquiler,
            inventario.c[inventario_id] == alquiler.c[alquiler_inventario],
        )
    )
    datos = pd.read_sql(consulta, con=engine)

    LOGGER.info(
        "Extracción SQL terminada: %s filas crudas, %s copias únicas y %s alquileres.",
        len(datos),
        datos["inventario_id"].nunique(),
        datos["alquiler_id"].notna().sum(),
    )
    return datos


def extraer_metas_csv(
    ruta: Path | str = RUTA_METAS_PREDETERMINADA,
    tiendas_esperadas: Collection[int] | None = None,
) -> pd.DataFrame:
    """Lee y valida el segundo origen antes de combinarlo con las métricas."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de metas: {ruta}")

    metas = pd.read_csv(ruta)
    if metas.columns.tolist() != COLUMNAS_METAS:
        raise ValueError(
            "El CSV de metas debe tener exactamente estas columnas y en este orden: "
            f"{COLUMNAS_METAS}. Se recibieron: {metas.columns.tolist()}."
        )
    if metas.empty:
        raise ValueError("El CSV de metas no puede estar vacío.")
    if metas.isna().any().any():
        columnas_con_nulos = metas.columns[metas.isna().any()].tolist()
        raise ValueError(f"El CSV de metas tiene nulos en: {columnas_con_nulos}.")

    try:
        metas["tienda_id"] = pd.to_numeric(metas["tienda_id"], errors="raise")
        metas["meta_rotacion"] = pd.to_numeric(metas["meta_rotacion"], errors="raise")
        metas["umbral_ocio_dias"] = pd.to_numeric(
            metas["umbral_ocio_dias"], errors="raise"
        )
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Las columnas del CSV de metas deben ser numéricas."
        ) from error

    columnas_enteras = ["tienda_id", "umbral_ocio_dias"]
    for columna in columnas_enteras:
        if not (metas[columna] % 1 == 0).all():
            raise ValueError(f"{columna} debe contener sólo números enteros.")
        metas[columna] = metas[columna].astype("int64")

    if metas["tienda_id"].duplicated().any():
        repetidas = metas.loc[metas["tienda_id"].duplicated(), "tienda_id"].tolist()
        raise ValueError(f"El CSV de metas repite tiendas: {repetidas}.")
    if (metas[["meta_rotacion", "umbral_ocio_dias"]] <= 0).any().any():
        raise ValueError("meta_rotacion y umbral_ocio_dias deben ser mayores que cero.")

    if tiendas_esperadas is not None:
        esperadas = {int(tienda) for tienda in tiendas_esperadas}
        encontradas = set(metas["tienda_id"])
        if encontradas != esperadas:
            raise ValueError(
                "Las tiendas del CSV no coinciden con SQL Server. "
                f"Esperadas: {sorted(esperadas)}. Encontradas: {sorted(encontradas)}."
            )

    LOGGER.info("Archivo de metas validado: %s tiendas (%s).", len(metas), ruta)
    return metas


def _validar_columnas_crudas(datos_crudos: pd.DataFrame) -> None:
    """Verifica el contrato entre la extracción y la transformación."""
    columnas_recibidas = datos_crudos.columns.tolist()
    if columnas_recibidas != COLUMNAS_CRUDAS:
        raise ValueError(
            "La extracción SQL no tiene las columnas esperadas. "
            f"Esperadas: {COLUMNAS_CRUDAS}. Recibidas: {columnas_recibidas}."
        )
    if datos_crudos.empty:
        raise ValueError("La extracción SQL no devolvió filas para transformar.")


def _validar_reglas_origen(
    datos_crudos: pd.DataFrame, alquileres: pd.DataFrame
) -> None:
    """Aplica las reglas de negocio que no admiten una corrección automática."""
    claves_copia = ["inventario_id", "pelicula_id", "titulo_pelicula", "tienda_id"]
    if datos_crudos[claves_copia].isna().any().any():
        columnas_con_nulos = (
            datos_crudos[claves_copia]
            .columns[datos_crudos[claves_copia].isna().any()]
            .tolist()
        )
        raise ValueError(
            "Hay copias sin identificador, película, título o tienda: "
            f"{columnas_con_nulos}."
        )

    copias_inconsistentes = (
        datos_crudos.groupby("inventario_id")[
            ["pelicula_id", "titulo_pelicula", "tienda_id"]
        ]
        .nunique(dropna=False)
        .gt(1)
        .any(axis=1)
    )
    if copias_inconsistentes.any():
        ids = copias_inconsistentes[copias_inconsistentes].index.tolist()
        raise ValueError(f"Hay copias asociadas a datos inconsistentes: {ids[:10]}.")

    if alquileres["alquiler_id"].duplicated().any():
        duplicados = alquileres.loc[
            alquileres["alquiler_id"].duplicated(), "alquiler_id"
        ].tolist()
        raise ValueError(f"Hay alquileres duplicados: {duplicados[:10]}.")
    if alquileres["fecha_alquiler"].isna().any():
        raise ValueError("Hay alquileres reales sin fecha de alquiler.")

    devolucion_previa = alquileres["fecha_devolucion"].notna() & (
        alquileres["fecha_devolucion"] < alquileres["fecha_alquiler"]
    )
    if devolucion_previa.any():
        ids = alquileres.loc[devolucion_previa, "alquiler_id"].tolist()
        raise ValueError(f"Hay devoluciones previas al alquiler: {ids[:10]}.")

    copias_validas = set(datos_crudos["inventario_id"])
    alquileres_sin_copia = ~alquileres["inventario_id"].isin(copias_validas)
    if alquileres_sin_copia.any():
        ids = alquileres.loc[alquileres_sin_copia, "alquiler_id"].tolist()
        raise ValueError(f"Hay alquileres sin copia de inventario: {ids[:10]}.")


def transformar(datos_crudos: pd.DataFrame, metas: pd.DataFrame) -> pd.DataFrame:
    """Calcula métricas de rotación y ociosidad sin recorrer filas.

    Conserva las copias sin alquileres en el denominador. Los alquileres sin
    devolución se conservan como registros válidos, pero no producen un
    intervalo de ociosidad artificial.
    """
    _validar_columnas_crudas(datos_crudos)
    datos = datos_crudos.copy()
    datos["fecha_alquiler"] = pd.to_datetime(datos["fecha_alquiler"], errors="raise")
    datos["fecha_devolucion"] = pd.to_datetime(
        datos["fecha_devolucion"], errors="raise"
    )

    alquileres = datos.loc[datos["alquiler_id"].notna()].copy()
    _validar_reglas_origen(datos, alquileres)

    copias = datos[
        ["inventario_id", "pelicula_id", "titulo_pelicula", "tienda_id"]
    ].drop_duplicates()
    alquileres = alquileres.sort_values(
        ["inventario_id", "fecha_alquiler", "alquiler_id"], kind="stable"
    ).copy()
    alquileres["devolucion_anterior"] = alquileres.groupby("inventario_id")[
        "fecha_devolucion"
    ].shift()

    # Se normalizan horas para reproducir DATEDIFF(DAY, ...) de SQL Server,
    # el mismo criterio usado y contrastado en el notebook.
    alquileres["dias_ociosidad"] = (
        alquileres["fecha_alquiler"].dt.normalize()
        - alquileres["devolucion_anterior"].dt.normalize()
    ).dt.days
    if (alquileres["dias_ociosidad"].dropna() < 0).any():
        raise ValueError("Se encontraron intervalos de ociosidad negativos.")

    claves_grupo = ["pelicula_id", "titulo_pelicula", "tienda_id"]
    copias_por_grupo = copias.groupby(claves_grupo, as_index=False).agg(
        cantidad_copias=("inventario_id", "nunique")
    )
    alquileres_por_grupo = alquileres.groupby(claves_grupo, as_index=False).agg(
        cantidad_alquileres=("alquiler_id", "nunique")
    )
    ociosidad_por_grupo = alquileres.groupby(claves_grupo, as_index=False).agg(
        promedio_dias_ociosidad=("dias_ociosidad", "mean")
    )

    resultado = (
        copias_por_grupo.merge(
            alquileres_por_grupo,
            on=claves_grupo,
            how="left",
            validate="one_to_one",
        )
        .merge(
            ociosidad_por_grupo,
            on=claves_grupo,
            how="left",
            validate="one_to_one",
        )
        .merge(metas, on="tienda_id", how="left", validate="many_to_one")
    )
    if (
        resultado["meta_rotacion"].isna().any()
        or resultado["umbral_ocio_dias"].isna().any()
    ):
        tiendas_sin_meta = sorted(
            resultado.loc[resultado["meta_rotacion"].isna(), "tienda_id"].unique()
        )
        raise ValueError(f"Hay tiendas sin metas para combinar: {tiendas_sin_meta}.")

    resultado["cantidad_alquileres"] = (
        resultado["cantidad_alquileres"].fillna(0).astype("int64")
    )
    if (resultado["cantidad_copias"] <= 0).any():
        raise ValueError("Hay grupos sin copias; no es posible calcular la rotación.")
    resultado["indice_rotacion"] = (
        resultado["cantidad_alquileres"] / resultado["cantidad_copias"]
    )
    resultado["cumple_meta_rotacion"] = (
        resultado["indice_rotacion"] >= resultado["meta_rotacion"]
    )
    resultado["requiere_revision_ocio"] = pd.Series(
        pd.NA, index=resultado.index, dtype="boolean"
    )
    ociosidad_medible = resultado["promedio_dias_ociosidad"].notna()
    resultado.loc[ociosidad_medible, "requiere_revision_ocio"] = (
        resultado.loc[ociosidad_medible, "promedio_dias_ociosidad"]
        > resultado.loc[ociosidad_medible, "umbral_ocio_dias"]
    )

    for columna in ["pelicula_id", "tienda_id", "cantidad_copias", "umbral_ocio_dias"]:
        resultado[columna] = resultado[columna].astype("int64")
    for columna in [
        "indice_rotacion",
        "promedio_dias_ociosidad",
        "meta_rotacion",
    ]:
        resultado[columna] = resultado[columna].round(6)

    resultado = resultado[COLUMNAS_DESTINO].sort_values(
        ["pelicula_id", "tienda_id"], kind="stable"
    )
    if resultado["pelicula_id"].isna().any() or resultado["tienda_id"].isna().any():
        raise ValueError("El resultado tiene claves de negocio nulas.")
    if resultado.duplicated(["pelicula_id", "tienda_id"]).any():
        raise ValueError("El resultado tiene combinaciones película–tienda duplicadas.")

    LOGGER.info(
        "Transformación terminada: %s filas, %s copias, %s alquileres y %s intervalos medibles.",
        len(resultado),
        int(resultado["cantidad_copias"].sum()),
        int(resultado["cantidad_alquileres"].sum()),
        int(alquileres["dias_ociosidad"].notna().sum()),
    )
    return resultado.reset_index(drop=True)


def cargar_destino(engine: Engine, resultado: pd.DataFrame) -> int:
    """Reemplaza el snapshot de destino dentro de una única transacción."""
    if resultado.columns.tolist() != COLUMNAS_DESTINO:
        raise ValueError(
            "El resultado no tiene el contrato de carga esperado. "
            f"Esperadas: {COLUMNAS_DESTINO}. Recibidas: {resultado.columns.tolist()}."
        )
    if resultado.empty:
        raise ValueError("No se carga una tabla destino vacía.")
    if resultado.duplicated(["pelicula_id", "tienda_id"]).any():
        raise ValueError("No se puede cargar un resultado con claves duplicadas.")

    with engine.begin() as conexion:
        asegurar_tabla_destino(conexion)
        conexion.execute(text("DELETE FROM [dbo].[TP2_RotacionInventario];"))
        resultado.to_sql(
            name=TABLA_DESTINO,
            con=conexion,
            schema=ESQUEMA_DESTINO,
            if_exists="append",
            index=False,
            dtype=TIPOS_CARGA_DESTINO,
            chunksize=100,
            method="multi",
        )
        filas_destino = conexion.execute(CONSULTA_CONTEO_DESTINO).scalar_one()
        if filas_destino != len(resultado):
            raise RuntimeError(
                "La cantidad cargada no coincide con la transformación: "
                f"destino={filas_destino}, resultado={len(resultado)}."
            )

    LOGGER.info("Carga terminada: %s filas en la tabla destino.", filas_destino)
    return int(filas_destino)


def configurar_logging(nivel: str) -> Path:
    """Configura logs simultáneos a consola y archivo para una ejecución CLI."""
    nivel_numerico = getattr(logging, nivel.upper(), None)
    if not isinstance(nivel_numerico, int):
        raise ValueError(f"Nivel de log inválido: {nivel}.")

    RUTA_LOG.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=nivel_numerico,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(RUTA_LOG, encoding="utf-8"),
        ],
        force=True,
    )
    return RUTA_LOG


def orquestar(ruta_metas: Path | str = RUTA_METAS_PREDETERMINADA) -> int:
    """Ejecuta extracción, transformación y carga; registra y propaga fallos."""
    engine: Engine | None = None
    try:
        LOGGER.info("Inicio del pipeline de rotación de inventario.")
        engine = get_engine()

        LOGGER.info("Inicio de extracción desde SQL Server.")
        datos_crudos = extraer_datos_sql(engine)
        LOGGER.info(
            "Fin de extracción SQL: %s filas, %s copias y %s alquileres.",
            len(datos_crudos),
            datos_crudos["inventario_id"].nunique(),
            datos_crudos["alquiler_id"].notna().sum(),
        )

        LOGGER.info("Inicio de extracción y validación del CSV de metas.")
        tiendas_sql = set(datos_crudos["tienda_id"].dropna().astype(int))
        metas = extraer_metas_csv(ruta_metas, tiendas_esperadas=tiendas_sql)
        LOGGER.info(
            "Fin de extracción CSV: %s metas para tiendas %s.",
            len(metas),
            sorted(tiendas_sql),
        )

        LOGGER.info("Inicio de transformación de métricas.")
        resultado = transformar(datos_crudos, metas)
        LOGGER.info(
            "Fin de transformación: %s combinaciones película–tienda.", len(resultado)
        )

        LOGGER.info(
            "Inicio de carga transaccional en %s.%s.", ESQUEMA_DESTINO, TABLA_DESTINO
        )
        filas_cargadas = cargar_destino(engine, resultado)
        LOGGER.info("Fin de carga: %s filas confirmadas.", filas_cargadas)
        LOGGER.info("Fin exitoso del pipeline.")
        return filas_cargadas
    except Exception:
        LOGGER.exception("El pipeline falló; la excepción se vuelve a propagar.")
        raise
    finally:
        if engine is not None:
            engine.dispose()


def _crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ETL de rotación de inventario por tienda.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--metas",
        type=Path,
        default=RUTA_METAS_PREDETERMINADA,
        help="Ruta al CSV complementario de metas por tienda.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Nivel mínimo que se registra en consola y archivo.",
    )
    return parser


def main(argumentos: Sequence[str] | None = None) -> int:
    """Punto de entrada de consola; las excepciones no se silencian."""
    args = _crear_parser().parse_args(argumentos)
    ruta_log = configurar_logging(args.log_level)
    LOGGER.info("Log de esta ejecución: %s", ruta_log)
    filas_cargadas = orquestar(args.metas)
    LOGGER.info(
        "Proceso finalizado correctamente con %s filas cargadas.", filas_cargadas
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
