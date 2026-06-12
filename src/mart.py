import pandas as pd
import json
from pathlib import Path
from datetime import datetime

print("=== Неделя 4: Витрина данных ===\n")

raw_path = "data/raw/variant_05/2026-05-16_20-22-10.json"
with open(raw_path, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

df = pd.DataFrame(raw_data['hourly'])
df['time'] = pd.to_datetime(df['time'])
df['city_id'] = 'US_NYC'
df['city_name'] = 'Нью-Йорк'
df['is_rainy'] = df['precipitation'] > 0
df['date'] = df['time'].dt.date
df['date'] = pd.to_datetime(df['date'])

numeric_cols = ['temperature_2m', 'relative_humidity_2m', 'precipitation', 'wind_speed_10m']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

mart_daily = df.groupby(['date', 'city_id', 'city_name']).agg({
    'temperature_2m': ['mean', 'max', 'min'],
    'relative_humidity_2m': 'mean',
    'precipitation': 'sum',
    'wind_speed_10m': 'max',
    'is_rainy': 'sum'
}).reset_index()

mart_daily.columns = [
    'date', 'city_id', 'city_name',
    'temp_mean_c', 'temp_max_c', 'temp_min_c',
    'humidity_mean_pct', 'precip_sum_mm', 'wind_max_kmh', 'rainy_hours_count'
]

mart_daily = mart_daily.sort_values('date')
mart_daily['temp_7d_avg'] = mart_daily['temp_mean_c'].rolling(7, min_periods=1).mean()
mart_daily['precip_7d_sum'] = mart_daily['precip_sum_mm'].rolling(7, min_periods=1).sum()

mart_dir = Path("data/mart/variant_05")
mart_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_path = mart_dir / f"mart_daily_{timestamp}.csv"
mart_daily.to_csv(output_path, index=False, encoding='utf-8')

print(f" Сохранено: {output_path}")
print(f" Строк: {len(mart_daily)}")
print(f" Дней: {mart_daily['date'].nunique()}")

print("\nПример витрины:")
print(mart_daily.head())