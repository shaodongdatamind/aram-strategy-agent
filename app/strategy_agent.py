from __future__ import annotations

import logging
from typing import List, Dict, Any
import json
import os

from .state import AgentState, StrategyDraft, BuildPlanStep, BuildItem
from .llm import OpenAIClient, format_strategy_prompt


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
    """
    Heuristic item plan constructor.

    Current behavior:
    - If the enemy comp contains notable healing, suggest up to two items with
      the tag "GrievousWounds" as an early counter step.

    Design intent:
    - Treat this as a pluggable rule-based stage that can be replaced or
      augmented by a learned/planned generator. Future versions may incorporate
      role, lane pressure, budget curves, and patch deltas.
    """
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


logger = logging.getLogger(__name__)


def generate_strategy(state: AgentState) -> StrategyDraft:
    """
    Compose a structured strategy draft from state.

    Flow:
    - Pick a coarse role from champion heuristics.
    - Build a plan using simple item-tag rules (see make_build_plan).
    - Summarize into a short TL;DR and attach evidence from items/snippets.

    Notes:
    - This function is the stand-in for an LLM-backed StrategyAgent. When
      replaced by an LLM, the same output schema (StrategyDraft) should be
      preserved so guardrails and downstream consumers remain stable.
    """
    patch = state.patch
    inputs = state.inputs
    my_champ = inputs.my_champ or (inputs.ally_comp[0] if inputs.ally_comp else "Unknown")
    enemy = inputs.enemy_comp or []
    facts = state.facts or {}
    items = facts.get("items", [])

    def fallback_strategy() -> StrategyDraft:
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

    # Try LLM-backed plan first (if API configured), else fallback to heuristics
    strict = os.environ.get("STRATEGY_LLM_STRICT", "0").lower() not in {"", "0", "false", "no"}
    try:
        client = OpenAIClient(model="gpt-4o-mini")
    except Exception:
        logger.exception("StrategyAgent: failed to initialize OpenAI client")
        if strict:
            raise
        return fallback_strategy()

    try:
        messages = format_strategy_prompt(
            patch=patch,
            inputs={
                "mode": inputs.mode,
                "ally_comp": inputs.ally_comp or [],
                "enemy_comp": inputs.enemy_comp or [],
                "my_champ": inputs.my_champ or my_champ,
                "question": inputs.question or "",
            },
            facts={"items": [i.model_dump() if hasattr(i, "model_dump") else i for i in items]},
            retrieval={"snippets": [s.model_dump() if hasattr(s, "model_dump") else s for s in (state.retrieval or {}).get("snippets", [])]},
            threat=state.threat or {},
        )
    except Exception:
        logger.exception("StrategyAgent: format_strategy_prompt failed")
        if strict:
            raise
        return fallback_strategy()

    try:
        # logger.info("StrategyAgent: messages: %s", messages)
        content = client.chat(messages, temperature=0.0, response_format={"type": "json_object"})
        # logger.info("StrategyAgent: chat output: %s", content)
    except Exception:
        logger.exception("StrategyAgent: OpenAI chat failed")
        if strict:
            raise
        return fallback_strategy()

    try:
        data: Dict[str, Any] = json.loads(content)
    except Exception:
        try:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = json.loads(content[start : end + 1])
            else:
                raise ValueError("No JSON object found in LLM content")
        except Exception:
            logger.exception("StrategyAgent: parsing LLM JSON failed; content snippet: %s", content[:300])
            if strict:
                raise
            return fallback_strategy()

    try:
        return StrategyDraft.model_validate(data)
    except Exception:
        logger.exception("StrategyAgent: StrategyDraft validation failed; data: %s", str(data)[:300])
        if strict:
            raise
        return fallback_strategy()


