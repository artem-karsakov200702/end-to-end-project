# Data Contract — variant_05

**Contract version:** 1.0
**Last updated:** 2026-06-12
**Project:** end-to-end weather pipeline
**Source:** Open-Meteo API (`/v1/forecast`)
**Layers:** raw → normalized → mart → PostgreSQL → DQ → BI / ML / LLM

---

## 1. Общая информация

| Параметр | Значение |
|---|---|
| Город | Нью-Йорк (40.7128, -74.006) |
| Country code | US |
| city_id | US_NYC |
| Endpoint | `https://api.open-meteo.com/v1/forecast` |
| Часовые параметры API | `temperature_2m`, `relative_humidity_2m`, `precipitation`, `wind_speed_10m` |
| Timezone хранения | UTC |

---

## 2. Naming & Units

- `snake_case` для всех колонок, только латиница и `_`.
- Суффиксы единиц: `*_c` (°C), `*_mm`, `*_kmh`, `*_pct`.
- Суффиксы агрегатов: `*_mean_*`, `*_min_*`, `*_max_*`, `*_sum_*`, `*_count`.
- Все timestamp-поля имеют суффикс `_utc` и хранятся в UTC.
- Float-значения округляются до 2 знаков, проценты записываются как `65.4`, а не `0.654`.

---

## 3. Слои данных

| Слой | Формат | Путь | Зерно |
|---|---|---|---|
| Raw | JSON | `data/raw/variant_05/` | Один снимок ответа API |
| Normalized | CSV | `data/normalized/variant_05/` | 1 строка = 1 час по 1 городу |
| Mart | CSV + Postgres | `data/mart/variant_05/`, `mart_weather_daily` | 1 строка = 1 день по 1 городу |

Business key витрины: `(date, city_id)`.

---

## 4. Normalized schema

| Поле | Тип | Nullable | Unit | Описание |
|---|---|---|---|---|
| `time` | datetime | no | UTC | Момент наблюдения |
| `city_id` | string | no | — | Идентификатор города |
| `city_name` | string | no | — | Название города |
| `latitude` | float | no | deg | Широта |
| `longitude` | float | no | deg | Долгота |
| `temperature_2m` | float | yes | °C | Температура воздуха |
| `relative_humidity_2m` | float | yes | % | Относительная влажность |
| `precipitation` | float | yes | mm | Осадки |
| `wind_speed_10m` | float | yes | km/h | Скорость ветра |
| `date` | date | no | — | Дата (производная) |
| `hour` | int | no | — | Час 0–23 (производная) |
| `is_rainy` | bool | no | — | Флаг `precipitation > 0` |

---

## 5. Mart schema (`mart_weather_daily`)

| Поле | Тип | Nullable | Unit | Описание |
|---|---|---|---|---|
| `date` | date | no | UTC day | Дата агрегации |
| `city_id` | string | no | — | Идентификатор города |
| `city_name` | string | no | — | Название города |
| `temp_mean_c` | float | yes | °C | Средняя дневная температура |
| `temp_max_c` | float | yes | °C | Максимальная температура |
| `temp_min_c` | float | yes | °C | Минимальная температура |
| `humidity_mean_pct` | float | yes | % | Средняя влажность |
| `precip_sum_mm` | float | yes | mm | Сумма осадков |
| `wind_max_kmh` | float | yes | km/h | Максимальная скорость ветра |
| `rainy_hours_count` | int | yes | hours | Часы с осадками |
| `temp_7d_avg` | float | yes | °C | 7-дневное скользящее среднее температуры |
| `precip_7d_sum` | float | yes | mm | 7-дневная скользящая сумма осадков |
| `created_at_utc` | datetime | no | UTC | Время построения строки |

---

## 6. Pipeline и state

- Запуск: `python -m src.pipeline --mode full | incremental`.
- State хранится в `data/state.json`: `last_watermark`, `last_run_at`, `last_status`.
- Watermark обновляется только после успешного `load`. При ошибке статус = `error`, watermark не сдвигается.
- Артефакты привязаны к периоду: `raw_<ds>.json`, `normalized_<ds>.csv`, `mart_daily_<ds>.csv`.

---

## 7. Orchestration

Airflow DAG `etl_variant_05`, schedule `*/5 * * * *`, цепочка: extract → normalize → build_mart → dq → load

- Период берётся из `data_interval_start` / `data_interval_end` / `ds`, не из `datetime.now()`.
- DQ Gate: при FAIL задача `dq` падает, `load` блокируется.
- Идемпотентность загрузки: `DELETE period + INSERT` в одной транзакции.

---

## 8. Data Quality Rules

| Правило | Уровень | Описание |
|---|---|---|
| `mart_non_empty` | FAIL | Витрина не пуста |
| `no_nulls_in_business_key` | FAIL | `date`, `city_id` не NULL |
| `unique_business_key` | FAIL | `(date, city_id)` уникален |
| `temp_min ≤ temp_mean ≤ temp_max` | FAIL | Корректное соотношение экстремумов |
| `temp_mean_range` | WARNING | `temp_mean_c` ∈ [-60, 60] |
| `humidity_range` | WARNING | `humidity_mean_pct` ∈ [0, 100] |
| `precip_non_negative` | FAIL | `precip_sum_mm ≥ 0` |
| `wind_non_negative` | FAIL | `wind_max_kmh ≥ 0` |
| `schema_columns_match_contract` | FAIL / WARNING | Соответствие схемы контракту |

Результат проверок: `docs/dq_report.json`.

SQL-проверка дублей:

```sql
SELECT date, city_id, COUNT(*) AS cnt
FROM mart_weather_daily
GROUP BY date, city_id
HAVING COUNT(*) > 1;
```

Пустой результат = требование уникальности выполнено.

---

## 9. ML-блок (поиск аномалий)

**Вход:** `data/normalized/variant_05/*.csv` (поля `time`, `temperature_2m`).
**Метод:** IQR — точка аномальна, если она вне `[Q1 − 1.5·IQR, Q3 + 1.5·IQR]`.
**Выход:**

- `docs/ml/anomalies_top.csv` — поля `time`, `date`, `hour`, `temperature_2m`, `z_score`, `iqr_lower_bound`, `iqr_upper_bound`, `distance_from_iqr_bound`. Допустим пустой файл с заголовками.
- `docs/ml/metrics.png` — график ряда температуры с границами IQR и аномалиями.
- `docs/ml/week13_summary.md` — текстовое резюме.

---

## 10. LLM-блок (report)

Отдельный шаг report, не встроенный в ETL: `src/llm/llm_summary.py`. Берёт агрегаты из mart, формирует строгий JSON-контекст, отправляет в LLM, проверяет числа в ответе на галлюцинации.

**Вход:** `data/mart/variant_05/mart_daily_*.csv`. Обязательные поля — `date`, `temp_mean_c`, `temp_max_c`, `temp_min_c`, `precip_sum_mm`, `wind_max_kmh`. Опциональные — `humidity_mean_pct`, `rainy_hours_count`, `temp_7d_avg`, `precip_7d_sum`.

**Переменные окружения (`.env`):**

| Переменная | Описание |
|---|---|
| `OPENAI_API_KEY` | Ключ LLM-провайдера (обязателен) |
| `OPENAI_MODEL` | Модель (`openai/gpt-4o-mini`) |
| `OPENAI_BASE_URL` | `https://openrouter.ai/api/v1` |
| `MART_DIR` | Путь к mart, по умолчанию `data/mart/variant_05` |
| `VARIANT` | Имя варианта, по умолчанию `variant_05` |

**Выход:**

- `docs/llm/context_used.json` — снапшот контекста (`dataset_identity`, `schema_hint`, `metrics`, `anomalies_top3_temperature_mean`, `constraints`).
- `docs/llm/summary.md` — сводка из 4 разделов: период и объём, ключевые метрики, последний день vs предыдущий, топ-3 аномалии.
- `docs/LLM_Usage_Log.md` — лог запусков (timestamp, model, PASS/FAIL, suspicious_numbers, prompt_len, answer_len).

**Правила:**

- В LLM передаются только агрегаты, не raw-данные.
- Все числа считает Python; LLM не выполняет арифметику.
- Каждое число из ответа должно совпадать с числом из контекста; даты и нумерация разделов исключаются из проверки.
- При обнаружении неподтверждённого числа скрипт завершается с кодом `1`, в лог пишется FAIL.
- Строки FAIL в логе не удаляются — они служат доказательством работы валидатора.

**Безопасность:** `OPENAI_API_KEY` хранится только в `.env` (исключён в `.gitignore`), в репозитории — только `.env.example` с пустыми значениями.

---

## 11. Структура репозитория

| Путь | Назначение |
|---|---|
| `configs/variant_05.yml` | Конфигурация варианта |
| `src/extract.py`, `src/normalize.py`, `src/mart.py`, `src/load.py` | Слои pipeline |
| `src/pipeline.py` | CLI-оркестратор |
| `src/dq.py`, `src/sql_checks.py` | Контроль качества |
| `src/llm/llm_summary.py` | LLM-блок report |
| `airflow/dags/etl_variant_05.py` | Производственный DAG |
| `data/raw|normalized|mart/variant_05/` | Слои данных |
| `data/state.json` | Watermark |
| `docs/Data_Contract.md` | Данный документ |
| `docs/dq_report.json` | Результат DQ |
| `docs/bi/`, `docs/airflow/`, `docs/ml/`, `docs/llm/` | Артефакты BI / Airflow / ML / LLM |
| `docs/LLM_Usage_Log.md` | Лог запусков LLM-блока |

---

## 12. Changelog

- **1.0 — 2026-06-12.** Финальная консолидированная версия. Добавлен LLM-блок (week14), описаны переменные окружения, выходные артефакты и анти-галлюцинационные правила. Удалена разбивка по неделям.
- **0.2 — 2026-06-01.** Зафиксированы naming/units rules, timezone-правила, гранулярность mart, авто-проверка схемы в `dq.py`.
- **0.1 — 2026-05-20.** Начальная версия: слои `raw`, `normalized`, `mart`, источник Open-Meteo.
