from __future__ import annotations

from typing import Any, Dict, List

from .state import AgentState, AgentInputs
from .db import load_patch_data
from .guide import fetch_guides
from .threat import compute_threat_scores
from .strategy_agent import generate_strategy
from .guardrail import guardrail_check


DEFAULT_PATCH = "14.99"


def node_load_patch_facts(state: AgentState) -> AgentState:
    items, champs, runes = load_patch_data(state.patch)
    state.facts = {
        "items": items,
        "champs": champs,
        "runes": runes,
    }
    state.retrieval = {"snippets": []}
    return state


def node_search_guides(state: AgentState) -> AgentState:
    """Fetch guides at runtime for relevant champions."""
    champ_names: List[str] = []
    if state.inputs.mode == "pre_game":
        champ_names = (state.inputs.ally_comp or []) + (state.inputs.enemy_comp or [])
    else:
        if state.inputs.my_champ:
            champ_names = [state.inputs.my_champ]
    
    snippets = fetch_guides(champ_names)
    state.retrieval = {"snippets": snippets}
    return state


def node_threat(state: AgentState) -> AgentState:
    scores = compute_threat_scores(state.patch, state.inputs.ally_comp or [], state.inputs.enemy_comp or [])
    state.threat = {"scores": scores}
    return state


def node_strategy(state: AgentState) -> AgentState:
    draft = generate_strategy(state)
    state.draft = draft
    return state


def node_guardrail(state: AgentState) -> AgentState:
    return guardrail_check(state, state.draft) if state.draft else state


def build_initial_state(patch: str, inputs: AgentInputs, profile: Dict[str, Any] | None = None) -> AgentState:
    return AgentState(patch=patch or DEFAULT_PATCH, inputs=inputs, profile=profile)


def run_pev(state: AgentState, max_loops: int = 1) -> AgentState:
    # plan -> evidence -> verify
    state = node_load_patch_facts(state)
    state = node_search_guides(state)
    state = node_threat(state)
    state = node_strategy(state)
    state = node_guardrail(state)
    loops = 0
    while state.verify and not state.verify.ok and loops < max_loops:
        state = node_strategy(state)
        state = node_guardrail(state)
        loops += 1
    return state


