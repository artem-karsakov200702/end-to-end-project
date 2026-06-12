# Сквозной ETL-проект: погода Нью-Йорка (variant_05)

End-to-end пайплайн обработки погодных данных: Open-Meteo API → нормализация → витрина → PostgreSQL → BI / ML / LLM.
Тема проекта — **погода в Нью-Йорке**, вариант **05**.

## Стек

Python, pandas, PostgreSQL, SQLAlchemy, Docker, Apache Airflow, Metabase, matplotlib, OpenAI / OpenRouter API.

## Структура проекта

```
src/
  extract.py          # запрос к Open-Meteo, raw JSON
  normalize.py        # raw → normalized CSV
  transform.py        # normalized → mart (агрегаты, rolling)
  load.py             # mart → PostgreSQL
  dq.py               # data quality проверки
  sql_checks.py       # SQL-проверки на mart
  pipeline.py         # единая точка входа ETL
  utils.py            # state.json, watermark
  llm/llm_summary.py  # LLM-сводка по mart (week 14)
airflow/dags/etl_variant_05.py
configs/variant_05.yml
data/raw|normalized|mart/variant_05/
data/state.json
docs/                 # Data_Contract.md, data_dictionary.md, dq_report.json, sql_checks.md,
                      # bi/, ml/, llm/, airflow/, LLM_Usage_Log.md
notebooks/            # week7_viz.ipynb, week13_ml.ipynb
tests/test_dq.py
```

## Установка окружения (Windows)

Базовая настройка через conda-скрипт:

1. Установите Miniconda или Anaconda.
2. Откройте папку проекта.
3. Дважды кликните `scripts\setup_env.bat` — скрипт создаст окружение `week1_env`, поставит зависимости из `requirements.txt` и запустит smoke test.

Если всё прошло успешно, в консоли появится:

```text
[OK]
```

Альтернатива через venv + Docker (для ETL, Airflow, Metabase, Postgres):

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
docker compose up -d
```

`docker compose` поднимает PostgreSQL (`weather_db`, user `user`, password `pase`, порт `5432`), Metabase и Airflow.

Если Postgres ставится локально (без Docker), скачайте его с [postgresql.org/download/windows](https://www.postgresql.org/download/windows/), пароль `pase`, порт `5432`.

## Запуск ETL

```powershell
# полный прогон
python -m src.pipeline --config configs/variant_05.yml --mode full

# инкрементальный прогон
python -m src.pipeline --config configs/variant_05.yml --mode incremental
```

Результат:

- `data/raw/variant_05/*.json` — сырые ответы API
- `data/normalized/variant_05/*.csv` — почасовые данные
- `data/mart/variant_05/mart_daily_*.csv` — дневная витрина
- таблица `mart_weather_daily` в PostgreSQL
- `data/state.json` — `last_watermark`, `last_run_at`, `last_status`

Повторный запуск идемпотентен: дубли по business key не появляются.

## Mart — гранулярность и KPI

Одна строка = один день по одному городу. Business key: `date + city_id`.

| Колонка | Смысл |
|---|---|
| temp_mean_c | средняя температура за день |
| temp_min_c / temp_max_c | минимальная / максимальная температура |
| temp_range_c | диапазон температуры (max − min) |
| humidity_mean_pct | средняя влажность |
| precip_sum_mm | сумма осадков |
| rainy_hours_count | количество часов с дождём |
| wind_max_kmh | максимальная скорость ветра |
| temp_7d_avg | 7-дневное скользящее среднее температуры |

## Data Quality

```powershell
python src/dq.py        # отчёт → docs/dq_report.json
python -m pytest -q     # unit-тесты в tests/
```

Проверки: непустота витрины, отсутствие NULL в business key, уникальность business key, диапазоны температуры, неотрицательность осадков, соответствие схемы `Data Contract`.

SQL-проверки на загруженной таблице:

```powershell
python src/sql_checks.py
```

## Airflow

DAG `etl_variant_05`: порядок задач `extract → transform → dq → load`. UI: http://localhost:8080.

- period-aware: используются `data_interval_start`, `data_interval_end`, `ds`
- артефакты per-run: `raw_<ds>.json`, `normalized_<ds>.csv`, `mart_daily_<ds>.csv`
- DQ — quality gate перед `load`
- идемпотентный `load`: `delete period + insert` — rerun не создаёт дублей

Проверка отсутствия дублей в БД:

```sql
SELECT date, city_id, COUNT(*) AS cnt
FROM mart_weather_daily
GROUP BY date, city_id
HAVING COUNT(*) > 1;
```

## BI (Metabase)

Metabase: http://localhost:3000. Подключение к БД:

- Host: `postgres`, Port: `5432`
- Database: `weather_db`, User: `user`, Password: `pase`

Дашборд по `mart_weather_daily` с тремя визуализациями: линейный график средней температуры, столбчатый по осадкам, таблица/график по ветру и влажности. Скриншоты — `docs/bi/`.

## Визуализация (week 7)

`notebooks/week7_viz.ipynb` — анализ mart-витрины: временной ряд, распределение, ranking. PNG-графики сохраняются в `notebooks/`.

## ML (week 13)

`notebooks/week13_ml.ipynb` — поиск аномалий температуры методом IQR (без supervised-модели, так как нет готового `target`).

- границы: `Q1 − 1.5·IQR` … `Q3 + 1.5·IQR`
- дополнительно считается `z_score`
- артефакты: `docs/ml/anomalies_top.csv`, `docs/ml/metrics.png`

## LLM summary (week 14)

Отдельный скрипт-шаг — человекочитаемая сводка по mart-витрине. Все числа считает Python; LLM получает только маленький JSON-контекст и **не имеет права выдумывать значения** — корректность чисел проверяется автоматически.

Подготовка:

```powershell
copy .env.example .env
# открой .env и впиши OPENAI_API_KEY=sk-...
pip install openai pandas python-dotenv
```

Запуск:

```powershell
python -m src.llm.llm_summary
```

Шаги скрипта:

1. читает все `data/mart/variant_05/mart_daily_*.csv`;
2. считает агрегаты (min / max / mean, last vs prev, top-3 аномалии по IQR);
3. сохраняет контекст в `docs/llm/context_used.json`;
4. вызывает LLM (`gpt-4o-mini`, `temperature=0`);
5. валидирует все числа из ответа против контекста;
6. пишет `docs/llm/summary.md` и строку в `docs/LLM_Usage_Log.md`.

Если LLM выдумал число — скрипт завершится с кодом `1`, а в логе появится строка со статусом `FAIL` и списком подозрительных чисел.

Защита от галлюцинаций:

- Python считает все агрегаты до вызова LLM
- в промпте явный запрет: *Do not invent numbers / Use only provided metrics*
- `temperature=0`
- регексп-валидатор сверяет числа из ответа с множеством чисел из `context_used.json`
- полный аудит: контекст и лог запусков лежат в репозитории

## Безопасность

- `OPENAI_API_KEY` хранится только в `.env`, который добавлен в `.gitignore`
- в репозитории — только `.env.example` с пустыми значениями
- в LLM не передаются raw-данные и персональная информация — только агрегаты

## Документация

- `docs/Data_Contract.md` — контракт данных (normalized + mart, naming, units, versioning)
- `docs/data_dictionary.md` — словарь колонок mart
- `docs/sql_checks.md` — описание SQL-проверок
- `docs/dq_report.json` — последний отчёт DQ
- `docs/LLM_Usage_Log.md` — лог LLM-запусков
- `docs/bi/`, `docs/ml/`, `docs/llm/`, `docs/airflow/` — артефакты по соответствующим неделям
