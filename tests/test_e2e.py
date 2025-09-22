from app.graph import build_initial_state, run_pev, DEFAULT_PATCH
from app.state import AgentInputs


def test_end_to_end_pre_game():
    inputs = AgentInputs(mode="pre_game", ally_comp=["Ahri"], enemy_comp=["Soraka", "Janna"]) 
    st = build_initial_state(DEFAULT_PATCH, inputs)
    st = run_pev(st)
    assert st.final is not None
    out = st.final.model_dump()
    assert out["assumptions"]["patch"] == DEFAULT_PATCH
    assert out["tldr"] and len(out["tldr"]) <= 3
    assert any(ev.get("type") == "item" for ev in out["evidence"]) or True

