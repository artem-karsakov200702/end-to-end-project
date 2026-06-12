import urllib.parse
from sqlalchemy import create_engine, text

POSTGRES_USER = "user"
POSTGRES_PASSWORD = "pase"
POSTGRES_DB = "weather_db"
POSTGRES_HOST = "postgres"
POSTGRES_PORT = "5432"

TABLE_NAME = "mart_weather_daily"


def run_checks():
    print("=== SQL Checks ===\n")

    encoded_password = urllib.parse.quote_plus(POSTGRES_PASSWORD)
    database_url = (
        f"postgresql+psycopg2://{POSTGRES_USER}:{encoded_password}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    engine = create_engine(database_url)

    checks = {
        "1. Таблица не пустая": f"SELECT COUNT(*) FROM {TABLE_NAME};",
        "2. Диапазон дат": f"SELECT MIN(date), MAX(date) FROM {TABLE_NAME};",
        "3. NULL в ключевых колонках": (
            f"SELECT COUNT(*) FROM {TABLE_NAME} "
            "WHERE date IS NULL OR city_id IS NULL;"
        ),
        "4. Дубликаты по дате": (
            f"SELECT date, COUNT(*) FROM {TABLE_NAME} "
            "GROUP BY date HAVING COUNT(*) > 1;"
        ),
        "5. Средняя температура": f"SELECT AVG(temp_mean_c) FROM {TABLE_NAME};",
        "6. Максимальная температура": f"SELECT MAX(temp_max_c) FROM {TABLE_NAME};",
        "7. Минимальная температура": f"SELECT MIN(temp_min_c) FROM {TABLE_NAME};",
        "8. Сумма осадков": f"SELECT SUM(precip_sum_mm) FROM {TABLE_NAME};",
    }

    total_checks = len(checks)
    passed = 0
    warnings = 0
    failed = 0

    with engine.connect() as conn:
        for name, sql in checks.items():
            try:
                result = conn.execute(text(sql))
                rows = result.fetchall()
                print(f"{name}: {rows}")

                if name == "1. Таблица не пустая":
                    count = rows[0][0]
                    if count > 0:
                        passed += 1
                    else:
                        failed += 1

                elif name == "3. NULL в ключевых колонках":
                    nulls = rows[0][0]
                    if nulls == 0:
                        passed += 1
                    else:
                        warnings += 1

                elif name == "4. Дубликаты по дате":
                    if len(rows) == 0:
                        passed += 1
                    else:
                        warnings += 1

                else:
                    passed += 1

            except Exception as e:
                print(f"{name}: Ошибка - {e}")
                failed += 1

    print(
        f"\nDQ summary: PASS={passed} WARNING={warnings} "
        f"FAIL={failed} TOTAL={total_checks}"
    )
    print("\nПроверки завершены")

    if failed > 0:
        return "FAIL"
    if warnings > 0:
        return "WARNING"
    return "PASS"


if __name__ == "__main__":
    run_checks()