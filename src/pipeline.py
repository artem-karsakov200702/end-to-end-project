import argparse
from pathlib import Path

import pandas as pd
import yaml

from src.extract import extract
from src.transform import transform
from src.load import load_to_postgres
from src.dq import run_checks_for_period


def run_pipeline(config_path, mode="full", start=None, end=None, ds=None):
    print(f"\n{'=' * 60}")
    print("ETL Pipeline запущен")
    print(f"Режим: {mode}")
    print(f"Config: {config_path}")
    print(f"Период: start={start}, end={end}, ds={ds}")
    print(f"{'=' * 60}\n")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    variant_id = config["variant_id"]
    table_name = "mart_weather_daily"

    raw_path = None
    normalized_path = None
    mart_path = None
    mart_df = None

    try:
        if mode == "extract":
            print("--- STAGE 1: EXTRACT ---")
            raw_path = extract(config=config, start=start, end=end, ds=ds)
            print(f"raw saved: {raw_path}")

        elif mode == "transform":
            print("--- STAGE 2: TRANSFORM ---")
            raw_path = get_raw_path(variant_id=variant_id, ds=ds)
            print(f"raw used: {raw_path}")

            normalized_path, mart_path, mart_df = transform(
                raw_path=raw_path,
                variant_id=variant_id,
                start=start,
                end=end,
                ds=ds,
            )
            print(f"normalized saved: {normalized_path}")
            print(f"mart saved: {mart_path}")
            print(f"mart rows: {len(mart_df)}")

        elif mode == "dq":
            print("--- STAGE 3: DQ ---")
            mart_path = get_mart_path(variant_id=variant_id, ds=ds)
            print(f"mart used for dq: {mart_path}")

            dq_result = run_checks_for_period(
                mart_path=mart_path,
                variant_id=variant_id,
                ds=ds,
            )
            print(f"dq result: {dq_result}")

            if dq_result != "PASS":
                raise RuntimeError(f"DQ gate failed with result={dq_result}")

        elif mode == "load":
            print("--- STAGE 4: LOAD ---")
            mart_path = get_mart_path(variant_id=variant_id, ds=ds)
            print(f"mart used for load: {mart_path}")

            mart_df = pd.read_csv(mart_path)
            mart_df["date"] = pd.to_datetime(mart_df["date"])

            load_to_postgres(
                df=mart_df,
                table_name=table_name,
                start=start,
                end=end,
            )
            print(f"loaded rows to postgres: {len(mart_df)}")

        elif mode == "full":
            print("--- STAGE 1: EXTRACT ---")
            raw_path = extract(config=config, start=start, end=end, ds=ds)
            print(f"raw saved: {raw_path}")

            print("--- STAGE 2: TRANSFORM ---")
            normalized_path, mart_path, mart_df = transform(
                raw_path=raw_path,
                variant_id=variant_id,
                start=start,
                end=end,
                ds=ds,
            )
            print(f"normalized saved: {normalized_path}")
            print(f"mart saved: {mart_path}")
            print(f"mart rows: {len(mart_df)}")

            print("--- STAGE 3: DQ ---")
            dq_result = run_checks_for_period(
                mart_path=mart_path,
                variant_id=variant_id,
                ds=ds,
            )
            print(f"dq result: {dq_result}")

            if dq_result != "PASS":
                raise RuntimeError(f"DQ gate failed with result={dq_result}")

            print("--- STAGE 4: LOAD ---")
            load_to_postgres(
                df=mart_df,
                table_name=table_name,
                start=start,
                end=end,
            )
            print(f"loaded rows to postgres: {len(mart_df)}")

        else:
            raise ValueError(f"Неизвестный режим: {mode}")

        print("\nPipeline успешно завершён")
        return True

    except Exception as e:
        print(f"Pipeline failed: {e}")
        return False


def get_raw_path(variant_id: str, ds: str) -> Path:
    path = Path(f"data/raw/variant_{variant_id}/raw_{ds}.json")
    if not path.exists():
        raise FileNotFoundError(f"Raw file not found: {path}")
    return path


def get_mart_path(variant_id: str, ds: str) -> Path:
    path = Path(f"data/mart/variant_{variant_id}/mart_daily_{ds}.csv")
    if not path.exists():
        raise FileNotFoundError(f"Mart file not found: {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="ETL Pipeline for Weather Data")
    parser.add_argument("--config", type=str, required=True, help="Путь к config/variant_XX.yml")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["extract", "transform", "dq", "load", "full"],
        default="full",
    )
    parser.add_argument("--start", type=str, required=False, help="data_interval_start")
    parser.add_argument("--end", type=str, required=False, help="data_interval_end")
    parser.add_argument("--ds", type=str, required=False, help="logical date as YYYY-MM-DD")

    args = parser.parse_args()

    success = run_pipeline(
        config_path=args.config,
        mode=args.mode,
        start=args.start,
        end=args.end,
        ds=args.ds,
    )
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()