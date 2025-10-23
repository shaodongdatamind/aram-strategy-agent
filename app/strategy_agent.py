from __future__ import annotations

import logging
from typing import List, Dict, Any
import json

from .state import AgentState, StrategyDraft
from .llm import OpenAIClient, format_strategy_prompt



logger = logging.getLogger(__name__)


def generate_strategy(state: AgentState) -> StrategyDraft:
    """
    Generate a strategy draft from state.
    """
    patch = state.patch
    inputs = state.inputs
    facts = state.facts or {}
    items = facts.get("items", [])

    client = OpenAIClient(model="gpt-4o-mini")
    messages = format_strategy_prompt(
        patch=patch,
        inputs={
            "mode": inputs.mode,
            "ally_comp": inputs.ally_comp or [],
            "enemy_comp": inputs.enemy_comp or [],
            "my_champ": inputs.my_champ or "",
            "question": inputs.question or "",
        },
        facts={"items": [i.model_dump() if hasattr(i, "model_dump") else i for i in items]},
        retrieval={"snippets": [s.model_dump() if hasattr(s, "model_dump") else s for s in (state.retrieval or {}).get("snippets", [])]},
        threat=state.threat or {},
    )
    content = client.chat(messages, temperature=0.0, response_format={"type": "json_object"})
    data: Dict[str, Any] = json.loads(content)
    return StrategyDraft.model_validate(data)


