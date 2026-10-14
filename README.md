# TP2 — Data Analytics e Ingeniería de Datos sobre Sakila

## Estructura del proyecto

```text
tp2/
├── config_conexion.py              # Engine de SQL Server
├── esquema.py                       # Mapeo Sakila canónico → esquema en español
├── dicc/                            # Diccionario y extracción de esquemas MySQL/SQL Server
├── sql/
│   ├── actividad_0/
│   │   ├── reconciliar.py           # Reconciliación MySQL → SQL Server
│   │   └── reconciliacion.txt       # Reporte de conteos
│   └── actividad_1/
│       ├── conjunto_trabajo.sql     # Datos crudos para el análisis
│       └── metricas_rotacion.sql    # Métricas agregadas en T-SQL
├── notebooks/
│   └── analisis.ipynb               # Actividades 1, 2 y 3, ejecutado con salidas
├── informe/
│   ├── diagnostico_calidad.md       # Entregable de la Actividad 2
│   └── diagnostico_calidad.pdf      # Versión PDF del diagnóstico
│   ├── informe.md                   # Informe final de la Actividad 5
├── graficos/                        # PNG a 150 dpi de la Actividad 3
├── pipeline/
│   ├── pipeline_tp2.py              # ETL CLI idempotente de la Actividad 4
│   ├── datos/metas_rotacion_tienda.csv
│   └── evidencias/actividad_4_doble_ejecucion.txt
└── requirements.txt                 # Dependencias del entorno virtual
```

## Actividad 0 — Preparación y reconciliación

La actividad resuelve la conexión mediante, el diccionario que traduce los nombres canónicos de Sakila a los nombres en español de la base y la comparación de cantidad de filas entre MySQL y SQL Server.

Archivos principales:

- `config_conexion.py`
- `esquema.py`
- `dicc/sakila_mysql.py`
- `dicc/sakila_sqlserver.py`
- `sql/actividad_0/reconciliar.py`
- `sql/actividad_0/reconciliacion.txt`

## Actividad 1 — Integración SQL–Python

El notebook extrae el conjunto de trabajo desde SQL Server, calcula el índice de rotación y los días promedio de ociosidad por película y tienda, y repite las métricas en T-SQL y pandas para validarlas y medir sus tiempos.

Archivos principales:

- `notebooks/analisis.ipynb`
- `sql/actividad_1/conjunto_trabajo.sql`
- `sql/actividad_1/metricas_rotacion.sql`

## Actividad 2 — Diagnóstico de calidad de datos

Se realizó el reconocimiento del conjunto, el análisis de tipos, faltantes, duplicados, reglas de negocio, valores atípicos y los controles específicos de la variante. También se contrastaron controles equivalentes entre pandas y T-SQL.

Entregables:

- `informe/diagnostico_calidad.md`
- `informe/diagnostico_calidad.pdf`
- Secciones 13 a 16 de `notebooks/analisis.ipynb`

## Actividad 3 — Análisis y visualización narrativa

El notebook construye vistas de copias y alquileres. La evidencia no justifica redistribuir stock entre tiendas sólo por la rotación: sus medias son 3,50 y 3,52 alquileres por copia.

Entregables:

- `notebooks/analisis.ipynb`
- `graficos/01_rotacion_extremos_por_tienda.png`
- `graficos/02_ocio_por_tienda.png`
- `graficos/03_copias_vs_alquileres.png`

## Actividad 4 — Pipeline ETL reproducible

El script extrae inventario, películas y alquileres desde SQL Server, valida y combina las metas operativas del CSV, calcula la rotación y la ociosidad en forma vectorizada y reemplaza el snapshot `dbo.TP2_RotacionInventario` dentro de una transacción. La clave primaria `(pelicula_id, tienda_id)` y el reemplazo transaccional hacen idempotente la carga.

La evidencia de dos ejecuciones consecutivas está en `pipeline/evidencias/actividad_4_doble_ejecucion.txt`: ambas dejaron 1.521 filas y 1.521 claves únicas.

## Actividad 5 — Informe de conclusiones

El informe final está en `informe/informe.md`. Incluye la pregunta de negocio, el abordaje, decisiones de diseño, síntesis de calidad, los tres gráficos, hallazgos, limitaciones y dificultades. Markdown es uno de los formatos de entrega permitidos; si se genera un PDF, debe derivarse de esta fuente y conservar exactamente el mismo contenido, con un máximo de seis páginas.

El registro disponible de uso de IA se mantiene separado en `informe/anexo_ia.md` y sólo documenta interacciones verificables.

## Instalación y configuración local

Usar Python 3.12 o compatible y un entorno virtual del proyecto:

```bash
python3 -m venv venv_tp2
venv_tp2/bin/pip install -r requirements.txt
```

Definir las credenciales de SQL Server fuera del código, mediante variables de entorno o un archivo `.env` local no versionado:

```bash
export DB_SERVER='servidor'
export DB_NAME='base_de_datos'
export DB_USER='usuario'
export DB_PASSWORD='contrasena'
```

`config_conexion.py` lee esas cuatro variables y crea el engine `mssql+pyodbc` con ODBC Driver 18 for SQL Server. Las variables `MYSQL_*` sólo son necesarias para repetir la reconciliación de la Actividad 0 y se definen de forma análoga:

```bash
export MYSQL_HOST='servidor_mysql'
export MYSQL_DATABASE='sakila'
export MYSQL_USER='usuario_mysql'
export MYSQL_PASSWORD='contrasena_mysql'
export MYSQL_PORT='3306'
```

## Ejecutar y verificar el pipeline

Desde la raíz del repositorio, con las cuatro variables `DB_*` definidas:

```bash
venv_tp2/bin/python pipeline/pipeline_tp2.py --log-level INFO
```

El CSV de metas predeterminado es `pipeline/datos/metas_rotacion_tienda.csv`. Para usar otro archivo compatible:

```bash
venv_tp2/bin/python pipeline/pipeline_tp2.py --metas ruta/al/archivo.csv --log-level INFO
```

El proceso registra consola y `pipeline/logs/pipeline_tp2.log`. Para demostrar idempotencia, ejecutarlo dos veces seguidas y, después de cada ejecución, ejecutar [`sql/actividad_4/verificar_idempotencia.sql`](sql/actividad_4/verificar_idempotencia.sql). El total de filas debe coincidir con las claves únicas película–tienda y con el conteo informado por el log.
