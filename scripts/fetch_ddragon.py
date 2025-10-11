from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import httpx


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "patches"


VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
CDN_BASE = "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US"


def fetch_json(client: httpx.Client, url: str) -> Any:
    r = client.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def resolve_version(client: httpx.Client, patch: str | None) -> str:
    versions: List[str] = fetch_json(client, VERSIONS_URL)
    if not versions:
        raise RuntimeError("Failed to get versions from DDragon")
    if patch is None or patch == "latest":
        return versions[0]
    # Find first version starting with `<major>.<minor>`
    prefix = patch.strip()
    for v in versions:
        if v.startswith(prefix):
            return v
    raise ValueError(f"No DDragon version found matching patch prefix '{patch}'. Available head: {versions[:5]}")


def augment_functional_tags(item_name: str, item_id: int, tags: List[str]) -> List[str]:
    lowered = item_name.lower()
    out = set(tags)
    # Grievous Wounds
    if any(k in lowered for k in ["executioner", "mortal reminder", "chempunk", "morello", "oblivion", "thornmail"]):
        out.add("GrievousWounds")
    # Anti shield
    if "serpent" in lowered:
        out.add("AntiShield")
    # ArmorPen / MagicPen
    if any(k in lowered for k in ["mortal reminder", "lord dominik", "serpent", "black cleaver", "last whisper"]):
        out.add("ArmorPen")
    if any(k in lowered for k in ["shadowflame", "luden", "sorcerer", "void staff", "liandry"]):
        out.add("MagicPen")
    return sorted(out)


def load_items(client: httpx.Client, version: str) -> List[Dict[str, Any]]:
    url = f"{CDN_BASE.format(version=version)}/item.json"
    data = fetch_json(client, url)
    results: List[Dict[str, Any]] = []
    for k, v in data.get("data", {}).items():
        try:
            item_id = int(k)
        except Exception:
            continue
        name = v.get("name", str(item_id))
        price = int(v.get("gold", {}).get("total", 0))
        tags = list(v.get("tags", []) or [])
        tags = augment_functional_tags(name, item_id, tags)
        results.append({
            "id": item_id,
            "name": name,
            "price": price,
            "tags": tags,
        })
    results.sort(key=lambda x: x["id"])
    return results


def load_champs(client: httpx.Client, version: str) -> List[Dict[str, Any]]:
    url = f"{CDN_BASE.format(version=version)}/champion.json"
    data = fetch_json(client, url)
    results: List[Dict[str, Any]] = []
    for champ_name, v in data.get("data", {}).items():
        key = v.get("key", champ_name)
        name = v.get("name", champ_name)
        tags = v.get("tags", []) or []
        results.append({
            "key": str(key),
            "name": name,
            "tags": tags,
            "notes": None,
        })
    results.sort(key=lambda x: x["name"].lower())
    return results


def load_runes(client: httpx.Client, version: str) -> List[Dict[str, Any]]:
    url = f"{CDN_BASE.format(version=version)}/runesReforged.json"
    trees = fetch_json(client, url)
    results: List[Dict[str, Any]] = []
    for tree in trees:
        tree_name = tree.get("name", "Unknown")
        for slot in tree.get("slots", []):
            for rune in slot.get("runes", []):
                results.append({
                    "id": int(rune.get("id")),
                    "name": rune.get("name", ""),
                    "tree": tree_name,
                })
    results.sort(key=lambda x: x["id"])
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch full DDragon data into data/patches/<patch>/")
    parser.add_argument("--patch", default="latest", help="Patch prefix like 14.19 or 'latest' (dir name)")
    parser.add_argument("--language", default="en_US", help="Locale (not currently used; en_US default)")
    args = parser.parse_args()

    patch_dir_name = args.patch if args.patch != "latest" else None

    with httpx.Client() as client:
        version = resolve_version(client, None if args.patch == "latest" else args.patch)
        # If patch dir is unspecified or 'latest', derive from version major.minor
        if patch_dir_name is None:
            parts = version.split(".")
            patch_dir_name = f"{parts[0]}.{parts[1]}"

        target_dir = DATA_ROOT / patch_dir_name
        target_dir.mkdir(parents=True, exist_ok=True)

        items = load_items(client, version)
        champs = load_champs(client, version)
        runes = load_runes(client, version)

        (target_dir / "items.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        (target_dir / "champs.json").write_text(json.dumps(champs, ensure_ascii=False, indent=2), encoding="utf-8")
        (target_dir / "runes.json").write_text(json.dumps(runes, ensure_ascii=False, indent=2), encoding="utf-8")

        # Preserve guides.json if present; otherwise create an empty list
        guides_path = target_dir / "guides.json"
        if not guides_path.exists():
            guides_path.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"Wrote items/champs/runes to {target_dir} using DDragon version {version}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


