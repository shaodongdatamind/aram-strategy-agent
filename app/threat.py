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
    """
    Compute a very simple enemy-only threat score.

    Current behavior:
    - Iterates enemy champions and adds +1 for each matched keyword bucket in
      KEYWORD_THREATS, recording short "reasons" strings.
    - Ignores ally composition beyond the signature; does not use items/runes,
      stats, or patch diffs. This is intentionally lightweight for now.

    Desired (per README/design):
    - Patch-scoped, evidence-backed scoring that considers ally/enemy synergies,
      counters, item/rune interactions, and quantitative signals (e.g., ARAM win
      rates, damage profiles). The longer-term plan is a verified ThreatAgent
      whose outputs are auditable and grounded in facts for the active patch.
    """
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


