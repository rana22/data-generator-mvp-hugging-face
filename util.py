from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

def load_json_rows(path: str | Path) -> pd.DataFrame:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of row objects")
    return pd.DataFrame(data)

def save_dataframe(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv":
        df.to_csv(path, index=False)
    elif path.suffix.lower() == ".json":
        path.write_text(df.to_json(orient="records", indent=2), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported output format: {path.suffix}")


def rows_to_json(records: list[dict[str, Any]], path: str | Path) -> None:
    Path(path).write_text(json.dumps(records, indent=2), encoding="utf-8")

MISSING_STRINGS = {"", "na", "n/a", "none", "null", "nan", "not reported"}

def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    return isinstance(value, str) and value.strip().lower() in MISSING_STRINGS


def normalize_value(value: Any) -> str:
    if is_missing(value):
        return ""

    # 🔥 handle list-like values
    if isinstance(value, list):
        return " ".join(str(v) for v in value)

    # 🔥 handle JSON-encoded lists (your case)
    if isinstance(value, str):
        v = value.strip()
        if v.startswith("[") and v.endswith("]"):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return " ".join(str(x) for x in parsed)
            except Exception:
                pass
        return v

    return str(value).strip()

def build_level_map(node_tree_df: pd.DataFrame) -> dict[int, list[str]]:
    level_map: dict[int, list[str]] = {}

    for _, row in node_tree_df.iterrows():
        step = int(row["step"])
        node = str(row["parent"])
        level_map.setdefault(step, []).append(node)

    for step in level_map:
        level_map[step] = list(dict.fromkeys(level_map[step]))  # dedupe, preserve order

    return dict(sorted(level_map.items()))

def _json_safe(obj) -> str:
    return json.dumps(obj, default=str).replace("</", "<\\/")

