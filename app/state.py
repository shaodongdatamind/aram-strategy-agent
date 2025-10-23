from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict
from pydantic import BaseModel, conlist


class ItemRow(BaseModel):
    id: int
    name: str
    price: int
    stats: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    tags: List[str] = []


class ChampRow(BaseModel):
    key: str
    name: str
    tags: List[str] = []
    notes: Optional[str] = None


class RuneRow(BaseModel):
    id: int
    name: str
    tree: str


class Snippet(BaseModel):
    id: str
    champ: Optional[str] = None
    text: str


class ThreatScore(BaseModel):
    unit: str
    score: float
    reasons: List[str] = []


class BuildItem(BaseModel):
    id: int
    name: str


class BuildPlanStep(BaseModel):
    trigger: str
    items: conlist(BuildItem, min_length=1)
    why: str
    timing: Optional[str] = None


Role = Literal["peel", "engage", "poke", "zone", "front_to_back", "anti_dive"]


class StrategyDraft(BaseModel):
    tldr: conlist(str, max_length=3)
    assumptions: Dict[str, Any]
    threats: List[Dict[str, str]]
    role: Role
    build_plan: List[BuildPlanStep]
    evidence: List[Dict[str, Any]]


class StrategyFinal(StrategyDraft):
    pass


class VerifyInfo(BaseModel):
    ok: bool
    violations: Optional[List[Dict[str, Any]]] = None
    attempts: int = 0


class AgentInputs(BaseModel):
    mode: Literal["pre_game", "ingame_qa"]
    ally_comp: Optional[List[str]] = None
    enemy_comp: Optional[List[str]] = None
    question: Optional[str] = None
    my_champ: Optional[str] = None
    state: Optional[Dict[str, Any]] = None


class AgentState(BaseModel):
    patch: str
    profile: Optional[Dict[str, Any]] = None
    inputs: AgentInputs
    facts: Optional[Dict[str, List[Any]]] = None
    retrieval: Optional[Dict[str, List[Snippet]]] = None
    threat: Optional[Dict[str, List[ThreatScore]]] = None
    draft: Optional[StrategyDraft] = None
    final: Optional[StrategyFinal] = None
    verify: Optional[VerifyInfo] = None


class PreGameAdviceInput(BaseModel):
    patch: Optional[str] = None
    ally_comp: List[str]
    enemy_comp: List[str]
    profile: Optional[Dict[str, Any]] = None
    use_live: Optional[Dict[str, bool]] = None


class IngameQAInput(BaseModel):
    patch: Optional[str] = None
    question: str
    my_champ: str
    state: Optional[Dict[str, Any]] = None
    profile: Optional[Dict[str, Any]] = None

