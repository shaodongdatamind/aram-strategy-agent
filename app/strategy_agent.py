from __future__ import annotations

from typing import List, Dict, Any

from .state import AgentState, StrategyDraft, BuildPlanStep, BuildItem


def pick_role(my_champ: str, enemy_comp: List[str]) -> str:
    lower = my_champ.lower()
    if any(k in lower for k in ["ashe", "xerath", "ziggs", "lux"]):
        return "poke"
    if any(k in lower for k in ["leona", "malphite", "zac", "sion"]):
        return "engage"
    return "front_to_back"


def needs_anti_heal(enemy_comp: List[str]) -> bool:
    healing_champs = {"Soraka", "Sona", "Aatrox", "Vladimir", "Yuumi"}
    return any(c in healing_champs for c in enemy_comp)


def make_build_plan(items: List[Dict[str, Any]], enemy_comp: List[str]) -> List[BuildPlanStep]:
    steps: List[BuildPlanStep] = []
    if needs_anti_heal(enemy_comp):
        anti_heal_items = [i for i in items if "GrievousWounds" in i.get("tags", [])]
        chosen = [BuildItem(id=i["id"], name=i["name"]) for i in anti_heal_items[:2]]
        if chosen:
            steps.append(
                BuildPlanStep(
                    trigger="anti_heal",
                    items=chosen,
                    why="Counter heavy healing",
                    timing="early if they snowball",
                )
            )
    return steps


def generate_strategy(state: AgentState) -> StrategyDraft:
    patch = state.patch
    inputs = state.inputs
    my_champ = inputs.my_champ or (inputs.ally_comp[0] if inputs.ally_comp else "Unknown")
    enemy = inputs.enemy_comp or []
    facts = state.facts or {}
    items = facts.get("items", [])

    role = pick_role(my_champ, enemy)
    build_plan = make_build_plan([i.model_dump() if hasattr(i, "model_dump") else i for i in items], enemy)

    tldr = [
        f"Play {role}; respect enemy spikes.",
        "Group for fights; trade when sums up.",
    ]

    threats = [{"name": s.unit, "why": ", ".join(s.reasons) or "high impact"} for s in (state.threat or {}).get("scores", [])]

    evidence: List[Dict[str, Any]] = []
    if build_plan:
        for bi in build_plan[0].items:
            evidence.append({"type": "item", "id": bi.id})
    for sn in (state.retrieval or {}).get("snippets", []):
        evidence.append({"type": "snippet", "id": sn.id})

    assumptions = {
        "patch": patch,
        "ally_comp": inputs.ally_comp or [],
        "enemy_comp": enemy,
        "notes": "Local mock data; numbers match SQL source when enabled.",
    }

    return StrategyDraft(
        tldr=tldr,
        assumptions=assumptions,
        threats=threats,
        role=role,  # type: ignore
        build_plan=build_plan,
        evidence=evidence,
    )


