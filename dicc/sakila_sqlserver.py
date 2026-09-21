import json

from config_conexion import get_connection


def save_database_schema():
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            TABLE_NAME,
            COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        ORDER BY TABLE_NAME, ORDINAL_POSITION;
    """

    cursor.execute(query)

    schema = {}

    for table_name, column_name in cursor.fetchall():
        if table_name not in schema:
            schema[table_name] = []

        schema[table_name].append(column_name)

    cursor.close()
    connection.close()

    with open("sakila_schema.json", "w", encoding="utf-8") as file:
        json.dump(schema, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    save_database_schema()