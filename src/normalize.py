import pandas as pd
import json
from pathlib import Path
from datetime import datetime

raw_path = "data/raw/variant_05/2026-05-16_20-22-10.json"
with open(raw_path, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

df = pd.DataFrame(raw_data['hourly'])

df['latitude'] = raw_data['latitude']
df['longitude'] = raw_data['longitude']
df['elevation'] = raw_data['elevation']
df['city_id'] = 'US_NYC'
df['city_name'] = 'Нью-Йорк'

df['time'] = pd.to_datetime(df['time'])
numeric_cols = ['temperature_2m', 'relative_humidity_2m', 'precipitation', 'wind_speed_10m']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df['date'] = df['time'].dt.date
df['hour'] = df['time'].dt.hour
df['is_rainy'] = df['precipitation'] > 0

normalized_dir = Path("data/normalized/variant_05")
normalized_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_path = normalized_dir / f"{timestamp}.csv"
df.to_csv(output_path, index=False, encoding='utf-8')

print(f"Сохранено: {output_path}")
print(f"Строк: {len(df)}")