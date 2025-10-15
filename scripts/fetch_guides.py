from __future__ import annotations

import argparse
import json
import html
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx


DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "patches"


def slugify_champion(name: str) -> str:
    s = name.lower()
    s = s.replace("&", " and ")
    s = s.replace("'", "")
    s = s.replace(".", "")
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "", s)
    return s


BOILERPLATE_PATTERNS = [
    re.compile(r"U\.GG .* ARAM build shows best .* ARAM runes by WR and popularity", re.IGNORECASE),
    re.compile(r"offers a full LoL .* ARAM build", re.IGNORECASE),
]


def is_boilerplate(text: str) -> bool:
    return any(p.search(text) for p in BOILERPLATE_PATTERNS)


def fetch_ugg_aram(champ_name: str, client: httpx.Client) -> Optional[str]:
    slug = slugify_champion(champ_name)
    url = f"https://u.gg/lol/champions/aram/{slug}-aram"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = client.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return None
        html = resp.text
        # Prefer meta description, fallback to og:description, else title
        m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html, flags=re.IGNORECASE)
        if not m:
            m = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html, flags=re.IGNORECASE)
        if m:
            text = m.group(1).strip()
        else:
            m = re.search(r"<title>([^<]+)</title>", html, flags=re.IGNORECASE)
            text = m.group(1).strip() if m else None
        if not text:
            return None
        # Clean and trim
        text = html.unescape(text)
        # Drop boilerplate that isn't useful as a guide snippet
        if is_boilerplate(text):
            return None
        # Trim overly long descriptions
        if len(text) > 400:
            text = text[:397] + "..."
        return text
    except Exception:
        return None


def fetch_metasrc_aram(champ_name: str, client: httpx.Client) -> Optional[str]:
    slug = slugify_champion(champ_name)
    # METAsrc champion ARAM page (heuristic URL)
    url = f"https://www.metasrc.com/lol/aram/champion/{slug}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = client.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return None
        html_text = resp.text
        # Try meta description
        m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html_text, flags=re.IGNORECASE)
        if not m:
            m = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html_text, flags=re.IGNORECASE)
        text = m.group(1).strip() if m else None
        if not text:
            # fallback: first paragraph-like text (very heuristic)
            m = re.search(r"<p[^>]*>([^<]{40,400})</p>", html_text, flags=re.IGNORECASE)
            text = m.group(1).strip() if m else None
        if not text:
            return None
        text = html.unescape(text)
        if len(text) > 400:
            text = text[:397] + "..."
        return text
    except Exception:
        return None


def fetch_murderbridge_items(champ_name: str, client: httpx.Client, id_to_item: Dict[int, str], id_to_rune: Dict[int, str]) -> Optional[str]:
    name_enc = quote(champ_name)
    url = f"https://www.murderbridge.com/Champion/{name_enc}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = client.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return None
        html_text = resp.text
        # Extract item ids from DDragon item image URLs present in the page
        item_ids = []
        for m in re.finditer(r"/img/item/(\d+)\.png", html_text):
            try:
                iid = int(m.group(1))
            except Exception:
                continue
            if iid not in item_ids:
                item_ids.append(iid)

        item_names = [id_to_item[i] for i in item_ids if i in id_to_item]

        # Extract rune ids from alt="rune-<id>"
        rune_ids: List[int] = []
        for m in re.finditer(r"alt=\"rune-(\d+)\"", html_text):
            try:
                rid = int(m.group(1))
            except Exception:
                continue
            if rid not in rune_ids:
                rune_ids.append(rid)
        rune_names = [id_to_rune[r] for r in rune_ids if r in id_to_rune]

        # Heuristic: require at least 3 items or 3 runes to consider useful
        if len(item_names) < 3 and len(rune_names) < 3:
            return None

        parts: List[str] = []
        if item_names:
            core = ", ".join(item_names[:3])
            extras = ", ".join(item_names[3:8]) if len(item_names) > 3 else ""
            s = f"Items (popular): {core}"
            if extras:
                s += f"; options: {extras}"
            parts.append(s)
        if rune_names:
            parts.append("Runes: " + ", ".join(rune_names[:6]))

        return ". ".join(parts)
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch ARAM guide snippets into data/patches/<patch>/guides.json")
    parser.add_argument("--patch", required=True, help="Patch dir name like 15.20 or 14.99")
    parser.add_argument("--delay", type=float, default=0.4, help="Delay seconds between requests (politeness)")
    args = parser.parse_args()

    patch_dir = DATA_ROOT / args.patch
    champs_path = patch_dir / "champs.json"
    out_path = patch_dir / "guides.json"

    if not champs_path.exists():
        raise SystemExit(f"Missing {champs_path}")

    champs: List[Dict[str, Any]] = json.loads(champs_path.read_text(encoding="utf-8"))
    # Load local items/runes map to turn ids into names
    items_path = patch_dir / "items.json"
    runes_path = patch_dir / "runes.json"
    id_to_item: Dict[int, str] = {}
    id_to_rune: Dict[int, str] = {}
    try:
        items = json.loads(items_path.read_text(encoding="utf-8"))
        for it in items:
            id_to_item[int(it.get("id"))] = it.get("name")
    except Exception:
        id_to_item = {}
    try:
        runes = json.loads(runes_path.read_text(encoding="utf-8"))
        for rn in runes:
            id_to_rune[int(rn.get("id"))] = rn.get("name")
    except Exception:
        id_to_rune = {}

    results: List[Dict[str, Any]] = []
    with httpx.Client(follow_redirects=True) as client:
        for row in champs:
            name = row.get("name") or row.get("Name")
            if not name:
                continue
            # Try MurderBridge structured scrape first (items/runes), else U.GG, else METAsrc
            text = fetch_murderbridge_items(name, client, id_to_item, id_to_rune)
            if not text:
                text = fetch_ugg_aram(name, client)
            if not text:
                text = fetch_metasrc_aram(name, client)
            if text:
                results.append({
                    "id": slugify_champion(name),
                    "champ": name,
                    "text": text,
                })
            time.sleep(args.delay)

    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(results)} snippets to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


