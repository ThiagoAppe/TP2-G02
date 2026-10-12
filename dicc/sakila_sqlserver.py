import json
from pathlib import Path

from sqlalchemy import text

from config_conexion import get_engine


def save_database_schema():
    engine = get_engine()

    query = """
        SELECT
            TABLE_NAME,
            COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        ORDER BY TABLE_NAME, ORDINAL_POSITION;
    """

    schema = {}

    try:
        with engine.connect() as connection:
            result = connection.execute(text(query))

            for table_name, column_name in result:
                if table_name not in schema:
                    schema[table_name] = []

                schema[table_name].append(column_name)
    finally:
        engine.dispose()

    output_file = Path(__file__).with_name("sakila_schema.json")
    with output_file.open("w", encoding="utf-8") as file:
        json.dump(schema, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    save_database_schema()
