import logging
from app.graph import build_initial_state, run_pev, DEFAULT_PATCH
from app.state import AgentInputs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

inputs = AgentInputs(
    mode="pre_game", 
    ally_comp=[
        "Ahri", "Amumu", "Katarina", "Jarvan IV", "Ashe"
    ], 
    enemy_comp=[
        "Soraka","Janna","Jinx","Corki","Kled"
    ])
state = build_initial_state(patch="15.20", inputs=inputs)
state = run_pev(state)
print(state.final.model_dump_json(indent=2))