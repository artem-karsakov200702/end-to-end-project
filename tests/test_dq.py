import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from dq import (
    check_non_empty,
    check_no_nulls_in_key,
    check_unique_business_key,
    check_temp_range,
    check_precip_non_negative,
)


def test_check_non_empty_pass():
    df = pd.DataFrame({
        "date": ["2026-05-16"],
        "city_id": [1]
    })
    result = check_non_empty(df)
    assert result["status"] == "PASS"


def test_check_non_empty_fail():
    df = pd.DataFrame(columns=["date", "city_id"])
    result = check_non_empty(df)
    assert result["status"] == "FAIL"


def test_check_no_nulls_in_key_fail():
    df = pd.DataFrame({
        "date": [None],
        "city_id": [1]
    })
    result = check_no_nulls_in_key(df)
    assert result["status"] == "FAIL"


def test_check_unique_business_key_fail():
    df = pd.DataFrame({
        "date": ["2026-05-16", "2026-05-16"],
        "city_id": [1, 1]
    })
    result = check_unique_business_key(df)
    assert result["status"] == "FAIL"


def test_check_temp_range_warning():
    df = pd.DataFrame({
        "temp_mean_c": [-100, 20]
    })
    result = check_temp_range(df)
    assert result["status"] == "WARNING"


def test_check_precip_non_negative_fail():
    df = pd.DataFrame({
        "precip_sum_mm": [0, -1]
    })
    result = check_precip_non_negative(df)
    assert result["status"] == "FAIL"