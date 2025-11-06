from __future__ import annotations

from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import logging
import re
import httpx
logger = logging.getLogger(__name__)

from .state import ThreatScore
from .llm import OpenAIClient


def normalize_champ_name(name: str) -> str:
    """Normalize champion name for matching (lowercase, handle special cases)."""
    name = name.lower().strip()
    name = name.replace("'", "").replace(" ", "")
    # Handle Wukong as MonkeyKing
    if name == "wukong":
        name = "monkeyking"
    return name


def _load_live_winrates(champs: List[str], patch: str) -> Dict[str, float]:
    """
    Load live ARAM win rates from metasrc.com and return normalized values [0,1] for threat scoring.
    Normalize: (wr - 0.4) / 0.20, clamped to [0,1]. This maps 40% -> 0.0, 50% -> 0.5, 60% -> 1.0
    """
    try:
        url = "https://www.metasrc.com/lol/aram/stats"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            resp = client.get(url, headers=headers, timeout=30, follow_redirects=True)
            if resp.status_code != 200:
                logger.warning(f"metasrc.com returned status {resp.status_code}")
                return {c.lower(): 0.5 for c in champs}
            
            html = resp.text
            all_winrates: Dict[str, float] = {}
            
            # Parse HTML table structure
            tbody_match = re.search(r'<tbody[^>]*>(.*?)</tbody>', html, re.DOTALL | re.IGNORECASE)
            table_content = tbody_match.group(1) if tbody_match else html
            
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_content, re.DOTALL | re.IGNORECASE)
            
            for row in rows:
                # Extract champion name from link or span
                name_patterns = [
                    r'<a[^>]*href="[^"]*aram/build/[^"]*"[^>]*>([A-Z][a-zA-Z\']+)</a>',
                    r'<span[^>]*hidden[^>]*>([A-Z][a-zA-Z\']+)</span>',
                ]
                
                champ_name = None
                for name_pat in name_patterns:
                    name_match = re.search(name_pat, row, re.IGNORECASE)
                    if name_match:
                        champ_name = name_match.group(1).strip()
                        break
                
                if not champ_name:
                    continue
                
                # Extract win rate percentage (filter for reasonable ARAM range 35-65%)
                wr_matches = list(re.finditer(r'([0-9]{1,2}\.[0-9]+)%', row))
                for wr_match in wr_matches:
                    try:
                        wr_value = float(wr_match.group(1)) / 100.0
                        if 0.35 <= wr_value <= 0.65:
                            normalized = normalize_champ_name(champ_name)
                            all_winrates[normalized] = wr_value
                            break
                    except ValueError:
                        continue
        
        # Map to requested champions and normalize for threat scoring
        out: Dict[str, float] = {}
        for champ in champs:
            key = normalize_champ_name(champ)
            wr = all_winrates.get(key, 0.5)  # Default to 0.5 if not found
            norm = _clamp01((wr - 0.4) / 0.20)
            out[champ.lower()] = norm
        
        logger.debug(f"Loaded {len(out)} win rates for threat scoring")
        return out
    except Exception as e:
        logger.warning(f"Failed to load live win rates: {e}, using defaults")
        return {c.lower(): 0.5 for c in champs}


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def compute_threat_scores(patch: str, ally_comp: List[str], enemy_comp: List[str]) -> List[ThreatScore]:
    """
    Hybrid threat scoring:
    - Numeric prior per enemy: prior = 1 + 9 * normalized(win_rate), where normalized = (wr-0.4)/0.20 clamped to [0,1]
    - LLM adjusts per-champion final scores in [1,10], with 2–4 concise reasons
    - We clamp and validate; include prior as a driver note in reasons
    """
    # 1) Load normalized priors [0,1] from live source
    norm = _load_live_winrates(enemy_comp, patch)
    # priors_0_10: Dict[str, float] = {k: 1.0 + 9.0 * v for k, v in norm.items()}

    # 2) Minimal champion facts for ally+enemy (tags + brief spell summaries)
    facts = _load_min_champ_facts(patch, (ally_comp or []) + (enemy_comp or []))

    # 3) Prompt and LLM call
    messages = _format_threat_prompt(
        patch=patch,
        ally=ally_comp or [],
        enemy=enemy_comp or [],
        facts=facts,
        winrates=[
            {
                "champ": c,
                "normalized_prior_0_1": float(norm.get(c.lower(), 0.5)),
                # "prior_score_0_10": float(priors_0_10.get(c.lower(), 1.0 + 9.0 * 0.5)),
            }
            for c in (enemy_comp or [])
        ],
    )
    client = OpenAIClient(model="gpt-4o-mini")
    content = client.chat(messages, temperature=0.0, response_format={"type": "json_object"})

    # 4) Parse, clamp, validate; ensure all enemy champs present exactly once
    data: Dict[str, Any] = json.loads(content)
    threats_out = data.get("threats", data)
    if not isinstance(threats_out, list):
        raise ValueError("Threat LLM output malformed: expected list under 'threats' or top-level list")

    by_unit: Dict[str, Dict[str, Any]] = {}
    for obj in threats_out:
        if isinstance(obj, dict) and "unit" in obj:
            by_unit[str(obj["unit"])] = obj

    scores: List[ThreatScore] = []
    for champ in (enemy_comp or []):
        obj = by_unit.get(champ)
        if not obj:
            raise ValueError(f"Threat LLM output missing champion '{champ}'")
        try:
            val = float(obj.get("score"))
        except Exception:
            raise ValueError(f"Threat score not numeric for '{champ}'")
        # clamp 1..10
        if val < 1.0:
            val = 1.0
        if val > 10.0:
            val = 10.0
        reasons = obj.get("reasons") or []
        if not isinstance(reasons, list):
            reasons = [str(reasons)]
        reasons = [str(r) for r in reasons][:4]
        # Always append prior driver info
        prior_norm = float(norm.get(champ.lower(), 0.5))
        reasons = reasons or ["LLM-adjusted threat"]
        reasons.append(f"prior={prior_norm:.2f}")
        scores.append(ThreatScore(unit=champ, score=val, reasons=reasons))
    return scores


def _load_min_champ_facts(patch: str, champs: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Load minimal facts (tags + brief spells) from local champs data.
    """
    path = Path(__file__).resolve().parent.parent / "data" / "patches" / patch / "champs.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    by_name: Dict[str, Dict[str, Any]] = {str(row.get("name")): row for row in data if isinstance(row, dict)}
    result: Dict[str, Dict[str, Any]] = {}
    for name in champs:
        row = by_name.get(name)
        if not row:
            continue
        tags = row.get("tags", []) or []
        brief_spells: List[Dict[str, str]] = []
        for sp in (row.get("spells") or [])[:4]:
            nm = sp.get("name", "")
            desc = sp.get("description", "")
            brief_spells.append({"name": nm, "summary": _brief(desc)})
        result[name] = {"tags": tags, "spells": brief_spells}
    return result


def _brief(text: str, max_len: int = 140) -> str:
    s = re.split(r"[\.!?]", text or "", maxsplit=1)[0].strip()
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s


def _format_threat_prompt(
    patch: str,
    ally: List[str],
    enemy: List[str],
    facts: Dict[str, Dict[str, Any]],
    winrates: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    system = (
        "You are an ARAM threat scoring assistant. Return ONE JSON object ONLY with key 'threats' as an array of objects "
        "{unit: string, score: number (1-10), reasons: string[], drivers?: object, uncertainty?: number}. "
        "Consider ally synergies, enemy kits, CC chains, poke/sustain, spikes, and normalized ARAM win rates. "
        "Be concise, reasons ≤ 4, no extra keys."
    )
    user = {
        "patch": patch,
        "ally_comp": ally,
        "enemy_comp": enemy,
        "champs_facts": facts,
        "winrates": winrates,
        "constraints": {
            "score_range": [1, 10],
            "reasons_max": 4,
            "must_include": enemy,
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


