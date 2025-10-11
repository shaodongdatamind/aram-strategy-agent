from app.graph import build_initial_state, run_pev, DEFAULT_PATCH
from app.state import AgentInputs

inputs = AgentInputs(mode="pre_game", ally_comp=["Ahri"], enemy_comp=["Soraka","Janna"])
state = build_initial_state(DEFAULT_PATCH, inputs)
state = run_pev(state)
print(state.final.model_dump_json(indent=2))