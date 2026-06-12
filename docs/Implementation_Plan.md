# Implementation Plan — проект ETL (variant_05, Open-Meteo)

## Общая цель

Построить воспроизводимый, отказоустойчивый и оркестрируемый инкрементальный ETL-пайплайн:
**API → raw JSON → normalized CSV → mart CSV → PostgreSQL → BI / ML / LLM-отчётность**
с поддержкой full/incremental загрузки, стейт-менеджментом, DQ-гейтом, ML-слоем поиска аномалий и LLM-помощником аналитика с защитой от галлюцинаций.

---

## Неделя 1 — Окружение и структура

## Что сделано
- Развернуто Python-окружение в `.venv`, зафиксированы зависимости в `requirements.txt`.
- Создан скрипт автоматической установки `scripts/setup_env.bat`.
- Создан GitHub-репозиторий `end-to-end-project`.
- Сформирована структура папок: `data/{raw,normalized,mart}/variant_05`, `configs/`, `airflow/dags/`, `docs/`, `src/`, `notebooks/`, `scripts/`, `tests/`, `reference/`.

**Артефакты:** `scripts/setup_env.bat`, `requirements.txt`, GitHub-репозиторий.
**Статус:** завершено.

---

## Неделя 2 — Extract (HTTP / API)

## Что сделано
- Написан модуль `src/extract.py` для Open-Meteo API: обработка сетевых исключений, логирование, обязательный `timeout`.
- Создан конфиг `configs/variant_05.yml` с координатами и параметрами выбранного города.
- Справочник городов хранится в `reference/cities.csv`.
- Сырые ответы сохраняются неизменяемо в `data/raw/variant_05/raw_YYYY-MM-DD.json` (и временные снимки `YYYY-MM-DD_HH-MM-SS.json` при коротких прогонах из Airflow).

**Артефакты:** `src/extract.py`, `configs/variant_05.yml`, `reference/cities.csv`, `data/raw/variant_05/`.
**Статус:** завершено.

---

## Неделя 3 — Normalize (почасовой слой)
## Что сделано
- Исследовательский ноутбук `notebooks/week3_eda.ipynb` — разбор JSON-структуры API.
- `pd.json_normalize` раскрывает вложенные hourly-метрики, поле `time` приведено к `ts` (snake_case).
- Добавлен статический бизнес-ключ `city_id` для `variant_05`.
- Очистка от дубликатов и сохранение нормализованного слоя в `data/normalized/variant_05/normalized_YYYY-MM-DD.csv`.

**Артефакты:** `src/normalize.py`, `notebooks/week3_eda.ipynb`, `data/normalized/variant_05/`.
**Статус:** завершено.

---

## Неделя 4 — Mart (суточная витрина)
## Что сделано
- Логика построения витрины оформлена в `src/mart.py` (исторические эксперименты — в `src/transform.py`).
- Агрегация почасовых метрик в суточные (`groupby('date')`) с расчётом KPI:
  - `temp_mean_c`, `temp_max_c`, `temp_min_c`;
  - `precip_sum_mm`, `humidity_mean_pct`, `wind_max_kmh`;
  - `rainy_hours_count`, скользящие `temp_7d_avg`, `precip_7d_sum`.
- Сохранение в `data/mart/variant_05/mart_daily_YYYY-MM-DD.csv`.

**Артефакты:** `src/mart.py`, `src/transform.py`, `data/mart/variant_05/mart_daily_*.csv`.
**Статус:** завершено.

---

## Неделя 5 — Загрузка в PostgreSQL
## Что сделано
- В Docker развёрнут PostgreSQL 13, база `airflow`, пользователь `airflow`.
- Скрипт `src/load.py` с DDL таблицы `mart_weather_daily` и идемпотентным замещением данных.
- Ручные SQL-проверки структуры и связности оформлены в `src/sql_checks.py` и зафиксированы в `docs/sql_checks.md`.

**Артефакты:** `src/load.py`, `src/sql_checks.py`, `docs/sql_checks.md`, таблица `mart_weather_daily`.
**Статус:** завершено.

---

## Неделя 6 — ETL pipeline (full/incremental, state)
## Что сделано
- Логика разнесена по плоским модулям в `src/`: `extract.py`, `normalize.py`, `mart.py`, `load.py`, общий хелпер `utils.py`.
- Центральный CLI-оркестратор `src/pipeline.py` с режимами `--mode full | incremental`.
- Стейт-менеджмент: watermark `last_date` хранится в `data/state.json`.
- Импорты обеспечиваются через `src/__init__.py`; `scripts/setup_env.bat` экспортирует `PYTHONPATH` для запуска из любого места.

**Артефакты:** `src/pipeline.py`, `src/extract.py`, `src/normalize.py`, `src/mart.py`, `src/load.py`, `src/utils.py`, `data/state.json`.
**Статус:** завершено.

---

## Неделя 7 — Визуализация (matplotlib)
## Что сделано
- Ноутбук `notebooks/week7_viz.ipynb` строит три аналитических среза:
  - временной ряд температур (`week7_timeseries.png`);
  - гистограмма распределения средних температур (`week7_distribution.png`);
  - топ-5 дождливых дней (`week7_ranking.png`).
- Графики снабжены осями, легендами, сеткой и единицами (°C, %, мм, км/ч).

**Артефакты:** `notebooks/week7_viz.ipynb`, `notebooks/week7_*.png`.
**Статус:** завершено.

---

## Неделя 8 — Data Quality и тестирование
## Что сделано
- Модуль `src/dq.py` с 6 проверками (FAIL / WARNING):
  1. non-empty check;
  2. отсутствие NaN/Null в `date` и `city_id`;
  3. уникальность ключа `city_id + date`;
  4. температурный коридор `[-50, +60] °C`;
  5. `temp_min_c ≤ temp_mean_c ≤ temp_max_c`;
  6. неотрицательность осадков и ветра.
- Результаты пишутся в `docs/dq_report.json`.
- Unit-тесты `tests/test_dq.py` на `pytest` (позитив / негатив / граница).

**Артефакты:** `src/dq.py`, `tests/test_dq.py`, `docs/dq_report.json`.
**Статус:** завершено.

---

## Неделя 9 — Data Governance
## Что сделано
- Дата-контракт `docs/Data_Contract.md` (v1.0.0): типы, ограничения, nullable-политика, логические лимиты для всех метрик витрины `mart_weather_daily`.
- Словарь бизнес-терминов `docs/data_dictionary.md` с описанием полей таблицы.
- DQ-правила в `src/dq.py` приведены в соответствие с контрактом.

**Артефакты:** `docs/Data_Contract.md`, `docs/data_dictionary.md`.
**Статус:** завершено.

---

## Неделя 10 — Docker Compose + BI
## Что сделано
- `docker-compose.yml` поднимает PostgreSQL и BI-инфраструктуру в единой Docker-сети.
- Persistent volumes: `pgdata` (таблицы СУБД) и `metabase_data` (настройки BI).
- Внешний порт PostgreSQL переназначен на `5434` (внутри сети — стандартный `5432`).
- В BI подключена витрина `mart_weather_daily`, собран дашборд, экспорты сложены в `docs/bi/`.

| Volume | Назначение |
|---|---|
| `pgdata` | Таблицы PostgreSQL (БД `airflow`) |
| `metabase_data` | Настройки и дашборды BI |

**Артефакты:** `docker-compose.yml`, `docs/bi/chart_timeseries.png`, `docs/bi/chart_ranking.png`, `docs/bi/dashboard_overview.png`.
**Статус:** завершено.

---

## Неделя 11 — Apache Airflow
## Что сделано
- В `docker-compose.yml` добавлены сервисы Airflow Webserver и Scheduler (2.8.1).
- Локальные `airflow/dags/` и `src/` смонтированы в `/opt/airflow/dags/` и `/opt/airflow/src/`.
- Переменная окружения `PYTHONPATH=/opt/airflow/src` решает проблему импортов плоских модулей.
- В UI (`localhost:8080`) настроено подключение `postgres_default` к целевой БД.
- Скриншоты успешной интеграции — в `docs/airflow/` (`graph_view.png`, `successful_run.png`, `task_log.png`).

**Артефакты:** обновлённый `docker-compose.yml`, подключение `postgres_default`, `docs/airflow/*.png`.
**Статус:** завершено.

---

## Неделя 12 — Оркестрация, инкрементальность, DQ Gate
## Что сделано
- Финальный DAG `airflow/dags/etl_variant_05.py`, schedule `*/5 * * * *`:
  `extract → normalize → build_mart → data_quality_checks → load_to_postgres`.
- **Инкрементальность:** даты передаются через Jinja-шаблоны `{{ data_interval_start }}` / `{{ data_interval_end }}`; выходные файлы — `mart_daily_YYYY-MM-DD.csv` (и временные `mart_daily_YYYY-MM-DD_HH-MM-SS.csv` для отдельных DAG-ранов).
- **DQ Gate:** при FAIL DAG останавливается, `load_to_postgres` блокируется.
- **Идемпотентность:** в `src/load.py` стратегия `DELETE period + INSERT` в одной транзакции — повторный запуск за тот же день не создаёт дубликатов.
- Финальный прогон в UI Airflow — все задачи зелёные (см. `docs/airflow/successful_run.png`).

**Артефакты:** `airflow/dags/etl_variant_05.py`, идемпотентный `src/load.py`.
**Статус:** завершено.

---

## Неделя 13 — ML-слой (поиск аномалий)
## Что сделано
- Ноутбук `notebooks/week13_ml.ipynb` реализует поиск климатических аномалий методом IQR по `temp_mean_c` витрины `mart_weather_daily`.
- ML-анализ запускается только на данных, прошедших DQ-гейт недели 8.
- Автоматическая выгрузка результатов: CSV экстремальных дней, график и Markdown-резюме.

**Артефакты:** `notebooks/week13_ml.ipynb`, `docs/ml/week13_summary.md`, `docs/ml/metrics.png`, `docs/ml/anomalies_top.csv`.
**Статус:** завершено.

---

## Неделя 14 — LLM-помощник аналитика
## Что сделано
- **Отдельный шаг report** (вне ETL): `src/llm/llm_summary.py`. Не встроен в pipeline и не влияет на загрузку в БД.
- **Строгий контекст:** Python сам читает все `data/mart/variant_05/mart_daily_*.csv` и считает min/max/mean, last vs prev, дельты и топ-3 аномалии по IQR. В LLM уходит только маленький JSON со структурой `dataset_identity`, `schema_hint`, `metrics`, `anomalies_top3_temperature_mean`, `constraints`. Raw-данные не передаются.
- **Анти-галлюцинация на трёх уровнях:**
  1. system prompt с запретами *Do not invent numbers / Use only provided metrics / Do not perform arithmetic*;
  2. `temperature=0`;
  3. пост-валидатор `validate_numbers()` сверяет каждое число из ответа с разрешённым множеством из контекста (с учётом дат и нумерации разделов). Любое неподтверждённое число → FAIL и `exit 1`.
- **Аудит:** каждый запуск сохраняет сводку, снапшот контекста и строку в лог запусков (модель, PASS/FAIL, подозрительные числа, длины запроса и ответа).
- **Безопасность:** API-ключ хранится только в `.env` (исключён в `.gitignore`); в репозитории — `.env.example` с пустыми значениями. LLM-провайдер — OpenRouter, модель `openai/gpt-4o-mini`, обход региональных ограничений OpenAI без VPN.
- **Демонстрация валидатора:** в `docs/LLM_Usage_Log.md` сохранены реальные строки FAIL, пойманные на этапе доводки (фрагменты дат `-03`, `-06`, дефис в «Топ-3»). После ужесточения регулярки лог переходит в PASS — это подтверждает, что защита от галлюцинаций работает не на словах.

**Артефакты:** `src/llm/llm_summary.py`, `docs/llm/summary.md`, `docs/llm/context_used.json`, `docs/LLM_Usage_Log.md`, `.env.example`, `.gitignore`, раздел в `README.md`.
**Статус:** завершено. Проект готов к финальной сдаче и тегу `v1.0-final`.

