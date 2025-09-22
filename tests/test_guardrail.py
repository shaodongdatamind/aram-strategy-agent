from app.state import AgentState, AgentInputs, StrategyDraft, BuildPlanStep, BuildItem
from app.guardrail import guardrail_check


def make_state_with_items(patch: str = "14.99") -> AgentState:
    inputs = AgentInputs(mode="pre_game", ally_comp=["Ahri"], enemy_comp=["Soraka"]) 
    st = AgentState(patch=patch, inputs=inputs)
    st.facts = {
        "items": [
            {"id": 3123, "name": "Executioner's Calling", "price": 800, "tags": ["GrievousWounds"]},
        ]
    }
    return st


def test_guardrail_unknown_item():
    st = make_state_with_items()
    draft = StrategyDraft(
        tldr=["Do not say dragon."],
        assumptions={"patch": st.patch},
        threats=[],
        role="poke",
        build_plan=[BuildPlanStep(trigger="anti_heal", items=[BuildItem(id=999, name="Fake")], why="test")],
        evidence=[],
    )
    st = guardrail_check(st, draft)
    assert st.verify and not st.verify.ok
    assert any(v.get("type") == "unknown_item" for v in st.verify.violations)


def test_guardrail_ok():
    st = make_state_with_items()
    draft = StrategyDraft(
        tldr=["Group and poke.", "Buy anti-heal early."],
        assumptions={"patch": st.patch},
        threats=[],
        role="poke",
        build_plan=[BuildPlanStep(trigger="anti_heal", items=[BuildItem(id=3123, name="Executioner's Calling")], why="heal counter")],
        evidence=[{"type": "item", "id": 3123}],
    )
    st = guardrail_check(st, draft)
    assert st.verify and st.verify.ok
    assert st.final is not None

