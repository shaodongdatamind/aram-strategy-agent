from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from .state import ChampRow, ItemRow, RuneRow, Snippet


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "patches"


def load_patch_data(patch: str) -> Tuple[List[ItemRow], List[ChampRow], List[RuneRow], List[Snippet]]:
    patch_dir = DATA_DIR / patch
    if not patch_dir.exists():
        raise FileNotFoundError(f"No mock data for patch {patch}")

    def read_json(name: str):
        with open(patch_dir / f"{name}.json", "r", encoding="utf-8") as f:
            return json.load(f)

    items = [ItemRow.model_validate(obj) for obj in read_json("items")]
    champs = [ChampRow.model_validate(obj) for obj in read_json("champs")]
    runes = [RuneRow.model_validate(obj) for obj in read_json("runes")]
    guides = [Snippet.model_validate(obj) for obj in read_json("guides")]

    return items, champs, runes, guides


def build_name_index(items: List[ItemRow]) -> Dict[str, ItemRow]:
    return {i.name.lower(): i for i in items}


