from __future__ import annotations

from typing import List

from .state import ThreatScore


KEYWORD_THREATS = {
    "healer": ["Soraka", "Sona", "Yuumi"],
    "shield": ["Janna", "Karma"],
    "tank": ["Sion", "Zac", "Cho'Gath"],
    "poke": ["Ziggs", "Xerath", "Lux"],
}


def compute_threat_scores(ally_comp: List[str], enemy_comp: List[str]) -> List[ThreatScore]:
    scores: List[ThreatScore] = []
    for champ in enemy_comp:
        base = 1.0
        reasons: List[str] = []
        for label, champs in KEYWORD_THREATS.items():
            if champ in champs:
                base += 1.0
                reasons.append(f"enemy has {label}")
        scores.append(ThreatScore(unit=champ, score=base, reasons=reasons))
    return scores


