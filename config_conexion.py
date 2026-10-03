import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


load_dotenv()


def get_engine():
    connection_url = URL.create(
        "mssql+pyodbc",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_SERVER"),
        database=os.getenv("DB_NAME"),
        query={
            "driver": "ODBC Driver 18 for SQL Server",
            "TrustServerCertificate": "yes",
        },
    )

    return create_engine(connection_url)