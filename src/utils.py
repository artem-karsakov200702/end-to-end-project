import json
from pathlib import Path
from datetime import datetime

STATE_PATH = Path("data/state.json")


def load_state():
    if not STATE_PATH.exists():
        return {
            "variant_id": "05",
            "source_type": "open-meteo",
            "last_watermark": None,
            "last_run_at": None,
            "last_status": None
        }

    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_watermark():
    state = load_state()
    return state.get("last_watermark")


def update_watermark(new_watermark):
    state = load_state()
    state["last_watermark"] = new_watermark
    state["last_run_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["last_status"] = "success"
    save_state(state)