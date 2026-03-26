from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


JSONDict = Dict[str, Any]


def normalize_item_number(value: Any) -> Any:
    """Normalize item codes by removing leading zeros.

    Keeps non-string/non-int values unchanged and preserves None.
    """
    if value is None:
        return None
    if isinstance(value, (str, int)):
        s = str(value)
        # Keep a stable zero value if string was all zeros.
        stripped = s.lstrip("0")
        return stripped if stripped else "0"
    return value


def _should_normalize_field(field_name: str) -> bool:
    # Normalize ERP item-number fields (sales, delivery, billing references, etc.).
    return "item" in field_name.lower()


def normalize_record(record: Mapping[str, Any]) -> JSONDict:
    """Return a normalized copy of a JSON object."""
    normalized: JSONDict = {}
    for key, value in record.items():
        if _should_normalize_field(key):
            normalized[key] = normalize_item_number(value)
        else:
            normalized[key] = value
    return normalized


def load_jsonl_file(file_path: Path) -> List[JSONDict]:
    """Load a single JSONL file and return normalized rows."""
    rows: List[JSONDict] = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                # Skip malformed rows instead of failing the whole load.
                continue
            if isinstance(obj, dict):
                rows.append(normalize_record(obj))
    return rows


def iter_jsonl_files(root_dir: Path) -> Iterable[Path]:
    """Yield JSONL files recursively under root_dir."""
    yield from root_dir.rglob("*.jsonl")


def load_all_jsonl(root_dir: str | Path) -> Dict[str, List[JSONDict]]:
    """Load all JSONL files recursively and group rows by entity folder name.

    Example output key: "sales_order_headers".
    """
    root = Path(root_dir)
    data_by_entity: Dict[str, List[JSONDict]] = {}

    for file_path in sorted(iter_jsonl_files(root)):
        entity_name = file_path.parent.name
        rows = load_jsonl_file(file_path)
        data_by_entity.setdefault(entity_name, []).extend(rows)

    return data_by_entity
