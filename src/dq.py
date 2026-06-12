import json
from datetime import datetime
from pathlib import Path

import pandas as pd


EXPECTED_MART_COLUMNS = [
    "date",
    "city_id",
    "city_name",
    "temp_mean_c",
    "temp_max_c",
    "temp_min_c",
    "humidity_mean_pct",
    "precip_sum_mm",
    "wind_max_kmh",
    "rainy_hours_count",
    "temp_7d_avg",
    "precip_7d_sum",
]


def load_mart_by_path(mart_path: Path) -> pd.DataFrame:
    if not mart_path.exists():
        raise FileNotFoundError(f"Файл mart не найден: {mart_path}")

    df = pd.read_csv(mart_path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


def check_schema_columns(df: pd.DataFrame, expected_columns: list) -> dict:
    actual_columns = list(df.columns)
    missing_columns = [c for c in expected_columns if c not in actual_columns]
    extra_columns = [c for c in actual_columns if c not in expected_columns]

    if missing_columns:
        status = "FAIL"
        reason = "Есть отсутствующие колонки из Data Contract"
    elif extra_columns:
        status = "WARNING"
        reason = "Есть лишние колонки вне Data Contract"
    else:
        status = "PASS"
        reason = "Схема колонок соответствует Data Contract"

    return {
        "name": "schema_columns_match_contract",
        "status": status,
        "reason": reason,
        "details": {
            "missing_columns": missing_columns,
            "extra_columns": extra_columns,
            "actual_column_count": len(actual_columns),
            "expected_column_count": len(expected_columns),
        },
    }


def check_non_empty(df: pd.DataFrame) -> dict:
    ok = len(df) > 0
    return {
        "name": "mart_non_empty",
        "status": "PASS" if ok else "FAIL",
        "reason": "Таблица не пустая" if ok else "Таблица пустая",
        "details": {"rows": int(len(df))},
    }


def check_no_nulls_in_key(df: pd.DataFrame) -> dict:
    required_cols = ["date", "city_id"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return {
            "name": "no_nulls_in_business_key",
            "status": "FAIL",
            "reason": "Невозможно проверить NULL в business key: нет нужных колонок",
            "details": {"missing_columns": missing},
        }

    null_count = int(df[required_cols].isna().sum().sum())
    ok = null_count == 0
    return {
        "name": "no_nulls_in_business_key",
        "status": "PASS" if ok else "FAIL",
        "reason": "Нет NULL в business key" if ok else "Есть NULL в business key",
        "details": {"null_count": null_count},
    }


def check_unique_business_key(df: pd.DataFrame) -> dict:
    required_cols = ["date", "city_id"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return {
            "name": "unique_business_key",
            "status": "FAIL",
            "reason": "Невозможно проверить уникальность business key: нет нужных колонок",
            "details": {"missing_columns": missing},
        }

    dup_count = int(df.duplicated(subset=required_cols).sum())
    ok = dup_count == 0
    return {
        "name": "unique_business_key",
        "status": "PASS" if ok else "FAIL",
        "reason": "Business key уникален" if ok else "Найдены дубликаты business key",
        "details": {"duplicate_count": dup_count},
    }


def check_temp_range(df: pd.DataFrame, min_temp: float = -60, max_temp: float = 60) -> dict:
    col = "temp_mean_c"
    if col not in df.columns:
        return {
            "name": "temp_mean_range",
            "status": "FAIL",
            "reason": "Невозможно проверить диапазон температуры: нет колонки temp_mean_c",
            "details": {"missing_columns": [col]},
        }

    bad_count = int((~df[col].between(min_temp, max_temp)).sum())
    ok = bad_count == 0
    return {
        "name": "temp_mean_range",
        "status": "PASS" if ok else "WARNING",
        "reason": "Температура в допустимом диапазоне" if ok else "Есть значения вне диапазона",
        "details": {
            "out_of_range_count": bad_count,
            "min_allowed": min_temp,
            "max_allowed": max_temp,
        },
    }


def check_precip_non_negative(df: pd.DataFrame) -> dict:
    col = "precip_sum_mm"
    if col not in df.columns:
        return {
            "name": "precip_non_negative",
            "status": "FAIL",
            "reason": "Невозможно проверить осадки: нет колонки precip_sum_mm",
            "details": {"missing_columns": [col]},
        }

    bad_count = int((df[col] < 0).sum())
    ok = bad_count == 0
    return {
        "name": "precip_non_negative",
        "status": "PASS" if ok else "FAIL",
        "reason": "Осадки неотрицательны" if ok else "Есть отрицательные осадки",
        "details": {"negative_count": bad_count},
    }


def run_dq(df: pd.DataFrame) -> list:
    return [
        check_schema_columns(df, EXPECTED_MART_COLUMNS),
        check_non_empty(df),
        check_no_nulls_in_key(df),
        check_unique_business_key(df),
        check_temp_range(df),
        check_precip_non_negative(df),
    ]


def aggregate_status(results: list) -> str:
    statuses = [r["status"] for r in results]
    if "FAIL" in statuses:
        return "FAIL"
    if "WARNING" in statuses:
        return "WARNING"
    return "PASS"


def save_report(results: list, output_path: Path, ds: str) -> None:
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "ds": ds,
        "checks": results,
        "final_status": aggregate_status(results),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def run_checks_for_period(mart_path: Path, variant_id: str, ds: str) -> str:
    df = load_mart_by_path(mart_path)
    results = run_dq(df)

    report_path = Path(f"docs/airflow_reports/variant_{variant_id}/run_{ds}_dq_report.json")
    save_report(results, report_path, ds)

    print("DQ CHECK RESULTS")
    for r in results:
        print(f"{r['name']}: {r['status']} - {r['reason']}")

    final_status = aggregate_status(results)
    print(f"\nFinal DQ status: {final_status}")
    print(f"Report saved to: {report_path}")

    return final_status


if __name__ == "__main__":
    variant_id = "05"
    ds = datetime.utcnow().strftime("%Y-%m-%d")
    mart_path = Path(f"data/mart/variant_{variant_id}/mart_daily_{ds}.csv")
    result = run_checks_for_period(mart_path=mart_path, variant_id=variant_id, ds=ds)
    raise SystemExit(0 if result == "PASS" else 1)