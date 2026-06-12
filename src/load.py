from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text

POSTGRES_HOST = "postgres"
POSTGRES_PORT = "5432"
POSTGRES_DB = "weather_db"
POSTGRES_USER = "user"
POSTGRES_PASSWORD = "pase"


def get_engine():
    encoded_password = quote_plus(POSTGRES_PASSWORD)
    database_url = (
        f"postgresql+psycopg2://{POSTGRES_USER}:{encoded_password}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    return create_engine(database_url)


def ensure_table_exists(conn, table_name):
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            date DATE NOT NULL,
            city_id VARCHAR(10) NOT NULL,
            city_name VARCHAR(50),
            temp_mean_c FLOAT,
            temp_max_c FLOAT,
            temp_min_c FLOAT,
            humidity_mean_pct FLOAT,
            precip_sum_mm FLOAT,
            wind_max_kmh FLOAT,
            rainy_hours_count INTEGER,
            temp_7d_avg FLOAT,
            precip_7d_sum FLOAT,
            PRIMARY KEY (date, city_id)
        );
    """))


def load_to_postgres(df, table_name, start=None, end=None):
    engine = get_engine()
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date

    if df.empty:
        raise ValueError("Пустой DataFrame нельзя загружать в PostgreSQL")

    start_date = pd.to_datetime(start).date() if start else min(df["date"])
    end_date = pd.to_datetime(end).date() if end else (max(df["date"]) + pd.Timedelta(days=1))

    with engine.begin() as conn:
        ensure_table_exists(conn, table_name)

        delete_sql = text(f"""
            DELETE FROM {table_name}
            WHERE date >= :start_date
              AND date < :end_date
        """)

        deleted = conn.execute(
            delete_sql,
            {
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        print(
            f"Удалены строки за период [{start_date}, {end_date}): "
            f"{deleted.rowcount if deleted.rowcount is not None else 'unknown'}"
        )

        df.to_sql(table_name, conn, if_exists="append", index=False)

        print(f"LOAD завершён: загружено {len(df)} строк")
        print(f"Период загрузки: [{start_date}, {end_date})")