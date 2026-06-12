# SQL Проверки для недели 5

В этой неделе мы загрузили mart-файл `mart_daily_2026-05-16_23-25-57.csv` в таблицу `mart_weather_daily` Postgres и провели следующие проверки:

---

## 1. Таблица не пустая

```sql
SELECT COUNT(*) FROM mart_weather_daily;
Результат: 7 строк
```
Проверка, что данные действительно загружены.

## 2. Диапазон дат
```
SELECT MIN(date), MAX(date) FROM mart_weather_daily;
```
Результат: 2026-05-16 → 2026-05-22
Проверка корректного диапазона дат (7 дней: с 16 по 22 мая).

## 3. NULL в ключевых колонках
```
SELECT COUNT(*) FROM mart_weather_daily WHERE date IS NULL OR city_id IS NULL;
```
Результат: 0

Проверка отсутствия пустых значений в ключевых колонках (дата и ID города).

## 4. Дубликаты по бизнес-ключу (дата)
```
SELECT date, COUNT(*) 
FROM mart_weather_daily 
GROUP BY date 
HAVING COUNT(*) > 1;
```
Результат: 0 строк

Проверка, что повторные строки не создаются при идемпотентной загрузке (одна строка = один день).

## 5. Метрики температуры
```
SELECT AVG(temp_mean_c), MAX(temp_max_c), MIN(temp_min_c) FROM mart_weather_daily;
Результат: ~25.5°C, ~31.7°C, ~10.0°C
```

Проверка корректности агрегированных метрик температуры.

## 6. Аномалии температуры
```
SELECT COUNT(*) FROM mart_weather_daily WHERE temp_mean_c > 50 OR temp_mean_c < -30;
```
Результат: 0

Проверка отсутствия аномальных значений температуры.

## 7. Сумма осадков
```
SELECT SUM(precip_sum_mm) FROM mart_weather_daily;
```
Результат: (сумма осадков за все дни)

Проверка корректности суммирования осадков.

## 8. Отрицательные осадки
```
SELECT COUNT(*) FROM mart_weather_daily WHERE precip_sum_mm < 0;
```
Результат: 0