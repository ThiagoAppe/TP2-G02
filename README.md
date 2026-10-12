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
│   └── analisis.ipynb               # Actividades 1 y 2, ejecutado con salidas
├── informe/
│   ├── diagnostico_calidad.md       # Entregable de la Actividad 2
│   └── diagnostico_calidad.pdf      # Versión PDF del diagnóstico
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


## Configuración local (ENV)

DB_SERVER=
DB_NAME=
DB_USER=
DB_PASSWORD=


MYSQL_HOST=
MYSQL_DATABASE=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_PORT=