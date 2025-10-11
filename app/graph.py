from __future__ import annotations

from typing import Any, Dict, List

from .state import AgentState, AgentInputs
from .db import load_patch_data
from .retrieval import GuideRetriever
from .threat import compute_threat_scores
from .strategy_agent import generate_strategy
from .guardrail import guardrail_check


DEFAULT_PATCH = "14.99"


def node_retrieve(state: AgentState) -> AgentState:
    items, champs, runes, guides = load_patch_data(state.patch)
    state.facts = {
        "items": items,
        "champs": champs,
        "runes": runes,
        "guides": guides,
    }
    state.retrieval = {"snippets": []}
    return state


def node_retrieval_agent(state: AgentState) -> AgentState:
    guides = []
    if state.facts and "guides" in state.facts:
        guides = state.facts["guides"]  # type: ignore[assignment]
    retriever = GuideRetriever(guides)
    q_terms: List[str] = []
    if state.inputs.mode == "pre_game":
        q_terms = (state.inputs.ally_comp or []) + (state.inputs.enemy_comp or [])
    else:
        q_terms = [state.inputs.my_champ or ""]
        if state.inputs.question:
            q_terms += state.inputs.question.split()
    query = " ".join([t for t in q_terms if t])
    snippets = retriever.search(query=query, k=5)
    state.retrieval = {"snippets": snippets}
    return state


def node_threat(state: AgentState) -> AgentState:
    scores = compute_threat_scores(state.inputs.ally_comp or [], state.inputs.enemy_comp or [])
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
    state = node_retrieve(state)
    state = node_retrieval_agent(state)
    state = node_threat(state)
    state = node_strategy(state)
    state = node_guardrail(state)
    loops = 0
    while state.verify and not state.verify.ok and loops < max_loops:
        state = node_strategy(state)
        state = node_guardrail(state)
        loops += 1
    return state


