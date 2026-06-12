import json
import time
from pathlib import Path

import requests


def save_raw_json(data, variant_id, ds, output_dir="data/raw"):
    variant_dir = Path(output_dir) / f"variant_{variant_id}"
    variant_dir.mkdir(parents=True, exist_ok=True)

    output_path = variant_dir / f"raw_{ds}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return output_path


def extract(config, start=None, end=None, ds=None, timeout=30, max_retries=3, retry_delay=3):
    variant_id = config["variant_id"]
    source_type = config["source_type"]
    api_config = config["api"]

    base_url = api_config["base_url"]
    method = api_config["method"].upper()
    params = api_config.get("params", {}).copy()

    print(f"[{variant_id}] Источник: {source_type}")
    print(f"Метод: {method} {base_url}")
    print(f"Период: start={start}, end={end}, ds={ds}")

    if start:
        params["start_date"] = start[:10]
    if end:
        params["end_date"] = end[:10]

    session = requests.Session()

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Попытка запроса {attempt}/{max_retries}...")

            if method == "GET":
                response = session.get(base_url, params=params, timeout=timeout)
            else:
                response = session.request(method, base_url, params=params, timeout=timeout)

            response.raise_for_status()
            data = response.json()

            output_path = save_raw_json(data=data, variant_id=variant_id, ds=ds)
            print(f"OK: raw сохранён в {output_path}")
            return output_path

        except requests.exceptions.Timeout as e:
            print(f"WARNING: timeout на попытке {attempt}/{max_retries}: {e}")
            if attempt == max_retries:
                raise RuntimeError(
                    f"extract error after {max_retries} attempts: request timeout"
                )
            time.sleep(retry_delay)

        except requests.exceptions.RequestException as e:
            print(f"WARNING: request error на попытке {attempt}/{max_retries}: {e}")
            if attempt == max_retries:
                raise RuntimeError(
                    f"extract error after {max_retries} attempts: {e}"
                )
            time.sleep(retry_delay)

        except Exception as e:
            raise RuntimeError(f"extract error: {e}")