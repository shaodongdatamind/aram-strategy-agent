from __future__ import annotations

from typing import Dict, List, Set

from .state import AgentState, StrategyDraft, StrategyFinal, VerifyInfo, ItemRow


FORBIDDEN_SR_TERMS: Set[str] = {"dragon", "baron", "jungle", "rift herald"}


def guardrail_check(state: AgentState, draft: StrategyDraft) -> AgentState:
    violations: List[Dict] = []

    # TL;DR length
    if len(draft.tldr) > 3:
        violations.append({"type": "tldr_too_long"})

    # ARAM scoping
    text_blob = " ".join(draft.tldr).lower()
    if any(term in text_blob for term in FORBIDDEN_SR_TERMS):
        violations.append({"type": "sr_content"})

    # Items exist in facts for patch
    fact_items: List[ItemRow] = [
        i if isinstance(i, ItemRow) else ItemRow.model_validate(i)
        for i in (state.facts or {}).get("items", [])
    ]
    id_set = {i.id for i in fact_items}
    for step in draft.build_plan:
        for it in step.items:
            if it.id not in id_set:
                violations.append({"type": "unknown_item", "id": it.id})

    if violations:
        state.verify = VerifyInfo(ok=False, violations=violations, attempts=(state.verify.attempts + 1 if state.verify else 1))
        return state

    state.final = StrategyFinal(**draft.model_dump())
    state.verify = VerifyInfo(ok=True, violations=[], attempts=(state.verify.attempts + 1 if state.verify else 1))
    return state


