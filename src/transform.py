import json
from pathlib import Path

import pandas as pd


def transform(raw_path, variant_id, start=None, end=None, ds=None):
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    df = pd.DataFrame(raw_data["hourly"])

    df["latitude"] = raw_data.get("latitude")
    df["longitude"] = raw_data.get("longitude")
    df["elevation"] = raw_data.get("elevation")
    df["city_id"] = "US_NYC"
    df["city_name"] = "Нью-Йорк"

    df["time"] = pd.to_datetime(df["time"], utc=True)

    numeric_cols = [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if start:
        start_ts = pd.to_datetime(start, utc=True)
        df = df[df["time"] >= start_ts]

    if end:
        end_ts = pd.to_datetime(end, utc=True)
        df = df[df["time"] < end_ts]

    if df.empty:
        raise ValueError("После фильтрации по периоду данных не осталось")

    df["date"] = df["time"].dt.floor("D").dt.tz_localize(None)
    df["hour"] = df["time"].dt.hour
    df["is_rainy"] = df["precipitation"] > 0

    normalized_dir = Path(f"data/normalized/variant_{variant_id}")
    normalized_dir.mkdir(parents=True, exist_ok=True)
    normalized_path = normalized_dir / f"normalized_{ds}.csv"
    df.to_csv(normalized_path, index=False, encoding="utf-8")
    print(f"Normalized сохранён: {normalized_path}")

    mart_df = df.groupby(["date", "city_id", "city_name"], as_index=False).agg(
        temp_mean_c=("temperature_2m", "mean"),
        temp_max_c=("temperature_2m", "max"),
        temp_min_c=("temperature_2m", "min"),
        humidity_mean_pct=("relative_humidity_2m", "mean"),
        precip_sum_mm=("precipitation", "sum"),
        wind_max_kmh=("wind_speed_10m", "max"),
        rainy_hours_count=("is_rainy", "sum"),
    )

    mart_df = mart_df.sort_values(["city_id", "date"]).reset_index(drop=True)
    mart_df["temp_7d_avg"] = (
        mart_df.groupby("city_id")["temp_mean_c"]
        .transform(lambda s: s.rolling(7, min_periods=1).mean())
    )
    mart_df["precip_7d_sum"] = (
        mart_df.groupby("city_id")["precip_sum_mm"]
        .transform(lambda s: s.rolling(7, min_periods=1).sum())
    )

    mart_dir = Path(f"data/mart/variant_{variant_id}")
    mart_dir.mkdir(parents=True, exist_ok=True)
    mart_path = mart_dir / f"mart_daily_{ds}.csv"
    mart_df.to_csv(mart_path, index=False, encoding="utf-8")

    print(f"Mart сохранён: {mart_path}")
    return normalized_path, mart_path, mart_df