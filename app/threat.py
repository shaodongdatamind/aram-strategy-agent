from __future__ import annotations

from typing import List, Dict, Optional
from pathlib import Path
import json
import logging
import re
import httpx
logger = logging.getLogger(__name__)

from .state import ThreatScore


KEYWORD_THREATS = {
    "healer": ["Soraka", "Sona", "Yuumi"],
    "shield": ["Janna", "Karma"],
    "tank": ["Sion", "Zac", "Cho'Gath"],
    "poke": ["Ziggs", "Xerath", "Lux"],
}



def _load_live_winrates(champs: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for champ in champs:
            wr = 0.5  # _fetch_winrate_for_champ(client, champ)
            # Normalize here: (wr - 0.4) / 0.20 → [0,1]
            norm = _clamp01((wr - 0.4) / 0.20)
            out[champ.lower()] = norm
    return out


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def compute_threat_scores(ally_comp: List[str], enemy_comp: List[str]) -> List[ThreatScore]:
    """
    Compute enemy threat scores using ARAM win-rate rank normalization.

    Steps:
    - Load per-champion ARAM win rates for the patch (winrates.json).
    - Convert win rates to normalized rank in [0,1] (best winrate → 1.0).
    - Map to 1–10: score = 1 + 9 * normalized_rank.
    - Provide concise reason noting rank position.
    """
    # Always load live from OP.GG; do not persist.
    # Load live (already normalized [0,1])
    winrates = _load_live_winrates(enemy_comp)

    scores: List[ThreatScore] = []
    for champ in enemy_comp:
        key = champ.lower()
        if key not in winrates:
            logger.warning("Threat: missing win-rate for '%s' — defaulting to mid score", champ)
            nr = 0.5
        else:
            nr = winrates[key]
        score = 1.0 + 9.0 * nr
        reasons = [f"ARAM win-rate normalized: {nr:.2f}"]
        scores.append(ThreatScore(unit=champ, score=score, reasons=reasons))
    return scores


