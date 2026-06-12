"""
Week 14 — LLM-помощник аналитика.

Идея шага:
    1) Python САМ считает все агрегаты по mart-CSV (mart_daily_YYYY-MM-DD.csv).
    2) В LLM отправляется только маленький структурированный контекст (JSON)
       с явным запретом "придумывать" числа.
    3) После ответа LLM запускается числовой валидатор: каждое число из текста
       должно встречаться в контексте, иначе шаг падает с ошибкой.
    4) Сохраняются артефакты:
         docs/llm/summary.md          — итоговая сводка
         docs/llm/context_used.json   — снапшот контекста (для воспроизводимости)
         docs/LLM_Usage_Log.md        — лог запуска (append)

Запуск:
    python -m src.llm.llm_summary

Переменные окружения (см. .env.example):
    OPENAI_API_KEY    — ключ провайдера (обязателен)
    OPENAI_MODEL      — модель (например, openai/gpt-4o-mini для OpenRouter)
    OPENAI_BASE_URL   — base url (для OpenRouter: https://openrouter.ai/api/v1)
    MART_DIR          — путь к mart, по умолчанию data/mart/variant_05
    VARIANT           — имя варианта, по умолчанию variant_05
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # noqa: BLE001
    pass


# --------------------------------------------------------------------------- #
# Пути и конфиг
# --------------------------------------------------------------------------- #

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MART_DIR = ROOT / "data" / "mart" / "variant_05"
DOCS_DIR = ROOT / "docs"
LLM_DOCS_DIR = DOCS_DIR / "llm"
SUMMARY_PATH = LLM_DOCS_DIR / "summary.md"
CONTEXT_PATH = LLM_DOCS_DIR / "context_used.json"
LOG_PATH = DOCS_DIR / "LLM_Usage_Log.md"

MART_DIR = Path(os.getenv("MART_DIR", str(DEFAULT_MART_DIR)))
VARIANT = os.getenv("VARIANT", "variant_05")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

CANDIDATE_NUMERIC_COLS = [
    # --- variant_05 (твой mart) ---
    "temp_mean_c",
    "temp_max_c",
    "temp_min_c",
    "humidity_mean_pct",
    "precip_sum_mm",
    "wind_max_kmh",
    "rainy_hours_count",
    "temp_7d_avg",
    "precip_7d_sum",
    # --- запасные варианты ---
    "temperature_2m_mean", "temp_mean", "t_avg", "t_mean", "mean_temp",
    "temperature_mean", "tavg",
    "temperature_2m_max", "temp_max", "t_max", "max_temp",
    "temperature_max", "tmax",
    "temperature_2m_min", "temp_min", "t_min", "min_temp",
    "temperature_min", "tmin",
    "precipitation_sum", "precipitation", "precip", "rain_sum", "rain", "prcp",
    "windspeed_10m_max", "wind_max", "windspeed", "wind_speed", "wind",
]

CANDIDATE_DATE_COLS = ["date", "dt", "day", "observation_date", "observed_at", "ds"]

MEAN_TEMP_NAMES = {
    "temp_mean_c",
    "temperature_2m_mean", "temp_mean", "t_avg", "t_mean",
    "mean_temp", "temperature_mean", "tavg",
}


# --------------------------------------------------------------------------- #
# 1) Загрузка mart с автодетектом колонок
# --------------------------------------------------------------------------- #


def load_mart(mart_dir: Path) -> tuple[pd.DataFrame, str, list[str]]:
    files = sorted(mart_dir.glob("mart_daily_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"Не найдено ни одного mart_daily_*.csv в {mart_dir}. "
            "Проверь MART_DIR или запусти week-6/week-7 ETL."
        )

    frames = [pd.read_csv(f) for f in files]
    df = pd.concat(frames, ignore_index=True)

    date_col = next((c for c in CANDIDATE_DATE_COLS if c in df.columns), None)
    if date_col is None:
        raise ValueError(
            f"В mart не нашлось колонки даты. Ожидал одно из: {CANDIDATE_DATE_COLS}. "
            f"Реальные колонки: {list(df.columns)}"
        )

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col).reset_index(drop=True)

    numeric_cols = [c for c in CANDIDATE_NUMERIC_COLS if c in df.columns]
    if not numeric_cols:
        raise ValueError(
            "В mart не нашлось ни одной известной числовой колонки. "
            f"Реальные колонки: {list(df.columns)}"
        )

    print(f"[week14] date_col = {date_col}")
    print(f"[week14] numeric_cols = {numeric_cols}")
    return df, date_col, numeric_cols


# --------------------------------------------------------------------------- #
# 2) Метрики и аномалии
# --------------------------------------------------------------------------- #


@dataclass
class Metric:
    name: str
    min: float | None
    max: float | None
    mean: float | None
    last: float | None
    prev: float | None
    delta_last_vs_prev: float | None


def _round(x: Any, n: int = 2) -> float | None:
    if x is None or pd.isna(x):
        return None
    return round(float(x), n)


def compute_metrics(df: pd.DataFrame, numeric_cols: list[str]) -> list[Metric]:
    metrics: list[Metric] = []
    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        last = s.iloc[-1]
        prev = s.iloc[-2] if len(s) >= 2 else None
        metrics.append(
            Metric(
                name=col,
                min=_round(s.min()),
                max=_round(s.max()),
                mean=_round(s.mean()),
                last=_round(last),
                prev=_round(prev),
                delta_last_vs_prev=_round(last - prev) if prev is not None else None,
            )
        )
    return metrics


def top_anomalies(df: pd.DataFrame, date_col: str, col: str, k: int = 3) -> list[dict]:
    if col not in df.columns:
        return []
    s = pd.to_numeric(df[col], errors="coerce")
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask = (s < low) | (s > high)
    anomalies = df.loc[mask, [date_col, col]].copy()
    anomalies["deviation"] = (s[mask] - s.median()).abs()
    anomalies = anomalies.sort_values("deviation", ascending=False).head(k)
    return [
        {"date": d.strftime("%Y-%m-%d"), "value": _round(v)}
        for d, v in zip(anomalies[date_col], anomalies[col])
    ]


def build_context(df: pd.DataFrame, date_col: str, numeric_cols: list[str]) -> dict:
    metrics = compute_metrics(df, numeric_cols)
    mean_col = next(
        (c for c in numeric_cols if c in MEAN_TEMP_NAMES),
        numeric_cols[0],
    )

    return {
        "dataset_identity": {
            "source": "Open-Meteo",
            "variant": VARIANT,
            "granularity": "daily",
            "period_start": df[date_col].min().strftime("%Y-%m-%d"),
            "period_end": df[date_col].max().strftime("%Y-%m-%d"),
            "rows": int(len(df)),
        },
        "schema_hint": "Одна строка mart = одни сутки наблюдений по выбранному городу.",
        "metrics": [asdict(m) for m in metrics],
        "anomalies_top3_temperature_mean": top_anomalies(df, date_col, mean_col, k=3),
        "constraints": [
            "Do not invent numbers.",
            "Use only the numbers provided in 'metrics' and 'anomalies_top3_temperature_mean'.",
            "If a value is missing, explicitly say it is not available.",
            "Do not perform arithmetic that is not already in the context.",
        ],
    }


# --------------------------------------------------------------------------- #
# 3) Промпт
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = (
    "Ты — аккуратный аналитик данных. Тебе дают JSON с уже посчитанными агрегатами "
    "по дневной погодной витрине. Запрещено выдумывать числа, делать собственные "
    "арифметические вычисления и ссылаться на данные, которых нет в JSON. "
    "Все числа в твоём ответе обязаны буквально совпадать с числами из JSON "
    "(включая знак и количество знаков после запятой). Если данных не хватает — "
    "честно скажи 'недостаточно данных'. Отвечай на русском, кратко, по делу."
)

USER_PROMPT_TEMPLATE = """\
Ниже — JSON-контекст по витрине погодных данных. Сформируй краткую сводку
(markdown), строго из 4 разделов:

1. Период и объём данных
2. Ключевые метрики (мин/макс/среднее по каждому показателю)
3. Последний день vs предыдущий (что выросло/упало)
4. Топ-3 аномалии температуры и возможная интерпретация

Жёсткие правила:
- используй только числа из JSON;
- если показателя нет — напиши «нет в данных»;
- не округляй и не пересчитывай числа;
- не добавляй дисклеймеров про "я ИИ".

JSON:
```json
{context_json}
```
"""


def render_user_prompt(context: dict) -> str:
    return USER_PROMPT_TEMPLATE.format(
        context_json=json.dumps(context, ensure_ascii=False, indent=2)
    )


# --------------------------------------------------------------------------- #
# 4) Вызов LLM
# --------------------------------------------------------------------------- #


def call_openai(system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY не задан. Заполни .env (см. .env.example) и попробуй снова."
        )

    from openai import OpenAI

    base_url = os.getenv("OPENAI_BASE_URL") or None
    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content or ""


# --------------------------------------------------------------------------- #
# 5) Анти-галлюцинация: проверка чисел в ответе
# --------------------------------------------------------------------------- #

# Число с возможным минусом. Минус — только если слева пробел/начало/скобка/=,
# иначе это дефис в словах «Топ-3», «week-13».
NUMBER_RE = re.compile(r"(?:(?<=^)|(?<=[\s(\[<=]))(-?\d+(?:[.,]\d+)?)")

# Даты в распространённых форматах: 2025-03-15, 2025/3/5, 15.03.2025.
DATE_IN_TEXT_RE = re.compile(r"\b\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}\b")


def _collect_allowed_numbers(context: dict) -> set[str]:
    allowed: set[str] = set()

    def add(value: Any) -> None:
        if value is None or isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            s = f"{float(value):.10f}".rstrip("0").rstrip(".")
            allowed.add(s if s else "0")
            if float(value).is_integer():
                allowed.add(str(int(value)))
        elif isinstance(value, str):
            for m in NUMBER_RE.findall(value):
                allowed.add(m.replace(",", "."))
        elif isinstance(value, dict):
            for v in value.values():
                add(v)
        elif isinstance(value, list):
            for v in value:
                add(v)

    add(context)
    return allowed


def _normalize(num_str: str) -> str:
    s = num_str.replace(",", ".")
    try:
        f = float(s)
    except ValueError:
        return s
    out = f"{f:.10f}".rstrip("0").rstrip(".")
    return out if out else "0"


def validate_numbers(text: str, context: dict) -> list[str]:
    cleaned = DATE_IN_TEXT_RE.sub(" ", text)
    allowed = _collect_allowed_numbers(context)
    suspicious: list[str] = []
    for raw in NUMBER_RE.findall(cleaned):
        norm = _normalize(raw)
        if norm in allowed:
            continue
        if norm in {str(i) for i in range(1, 11)}:
            continue
        suspicious.append(raw)
    return suspicious


# --------------------------------------------------------------------------- #
# 6) Запись артефактов
# --------------------------------------------------------------------------- #


def save_summary(text: str) -> None:
    LLM_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(text.strip() + "\n", encoding="utf-8")


def save_context_snapshot(context: dict) -> None:
    LLM_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    CONTEXT_PATH.write_text(
        json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def append_log(
    *, model: str, ok: bool, suspicious: list[str],
    user_prompt_len: int, answer_len: int,
) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    new_file = not LOG_PATH.exists()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status = "PASS" if ok else "FAIL"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        if new_file:
            f.write("# LLM Usage Log\n\n")
            f.write("Лог всех запусков `src/llm/llm_summary.py`.\n\n")
            f.write(
                "| Время (UTC) | Модель | Статус | Подозрительные числа | "
                "len(prompt) | len(answer) |\n"
            )
            f.write("|---|---|---|---|---|---|\n")
        susp = ", ".join(suspicious) if suspicious else "—"
        f.write(
            f"| {ts} | {model} | {status} | {susp} | "
            f"{user_prompt_len} | {answer_len} |\n"
        )


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def main() -> int:
    print(f"[week14] mart_dir = {MART_DIR}")
    df, date_col, numeric_cols = load_mart(MART_DIR)
    print(f"[week14] загружено строк: {len(df)}")

    context = build_context(df, date_col, numeric_cols)
    save_context_snapshot(context)
    print(f"[week14] контекст сохранён → {CONTEXT_PATH.relative_to(ROOT)}")

    user_prompt = render_user_prompt(context)
    answer = call_openai(SYSTEM_PROMPT, user_prompt)

    suspicious = validate_numbers(answer, context)
    ok = not suspicious

    save_summary(answer)
    append_log(
        model=MODEL, ok=ok, suspicious=suspicious,
        user_prompt_len=len(user_prompt), answer_len=len(answer),
    )
    print(f"[week14] summary сохранён → {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"[week14] log обновлён    → {LOG_PATH.relative_to(ROOT)}")

    if not ok:
        print(
            "[week14] В ответе LLM найдены числа, которых нет в контексте: "
            + ", ".join(suspicious)
        )
        print("         Перезапусти шаг или ужесточи промпт.")
        return 1

    print("[week14] Все числа в ответе совпадают с контекстом.")
    return 0


if __name__ == "__main__":
    sys.exit(main())