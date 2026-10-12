import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config_conexion import get_engine
from dicc.sakila_mysql import get_mysql_connection
from esquema import SCHEMA

OUTPUT_FILE = "reconciliacion.txt"


def count_mysql_rows(connection, table_name):
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    count = cursor.fetchone()[0]
    cursor.close()

    return count


def count_sql_server_rows(connection, table_name):
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
    count = cursor.fetchone()[0]
    cursor.close()

    return count


def reconcile_databases():
    mysql_connection = get_mysql_connection()
    sql_server_engine = get_engine()
    sql_server_connection = sql_server_engine.raw_connection()

    results = []

    try:
        for canonical_table, mapping in SCHEMA.items():
            sql_server_table = mapping["tabla"]

            mysql_count = count_mysql_rows(
                mysql_connection,
                canonical_table,
            )

            sql_server_count = count_sql_server_rows(
                sql_server_connection,
                sql_server_table,
            )

            difference = sql_server_count - mysql_count

            results.append(
                (
                    canonical_table,
                    mysql_count,
                    sql_server_count,
                    difference,
                )
            )
    finally:
        mysql_connection.close()
        sql_server_connection.close()
        sql_server_engine.dispose()

    return results


def save_report(results):
    headers = (
        "Tabla",
        "Filas origen",
        "Filas SQL Server",
        "Diferencia",
    )

    table_width = max(
        len(headers[0]),
        max(len(row[0]) for row in results),
    )

    header = (
        f"{headers[0]:<{table_width}} | "
        f"{headers[1]:>12} | "
        f"{headers[2]:>16} | "
        f"{headers[3]:>10}"
    )

    separator = "-" * len(header)

    lines = [
        "RECONCILIACIÓN MYSQL -> SQL SERVER",
        "",
        header,
        separator,
    ]

    for table_name, mysql_count, sql_server_count, difference in results:
        lines.append(
            f"{table_name:<{table_width}} | "
            f"{mysql_count:>12} | "
            f"{sql_server_count:>16} | "
            f"{difference:>10}"
        )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


if __name__ == "__main__":
    results = reconcile_databases()
    save_report(results)

    print(f"Reporte generado: {OUTPUT_FILE}")
