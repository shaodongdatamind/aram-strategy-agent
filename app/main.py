from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .state import PreGameAdviceInput, IngameQAInput, AgentInputs
from .graph import build_initial_state, run_pev, DEFAULT_PATCH


app = FastAPI(title="ARAM Coach", version="0.1.0")


@app.post("/pre_game_advice")
def pre_game_advice(body: PreGameAdviceInput):
    patch = body.patch or DEFAULT_PATCH
    if not body.ally_comp or not body.enemy_comp:
        raise HTTPException(status_code=400, detail="ally_comp and enemy_comp are required")
    inputs = AgentInputs(mode="pre_game", ally_comp=body.ally_comp, enemy_comp=body.enemy_comp)
    state = build_initial_state(patch=patch, inputs=inputs, profile=body.profile)
    state = run_pev(state)
    if not state.final:
        raise HTTPException(status_code=500, detail={"verify": state.verify.model_dump() if state.verify else None})
    return state.final.model_dump()


@app.post("/ingame_qa")
def ingame_qa(body: IngameQAInput):
    patch = body.patch or DEFAULT_PATCH
    inputs = AgentInputs(mode="ingame_qa", my_champ=body.my_champ, question=body.question, state=body.state)
    state = build_initial_state(patch=patch, inputs=inputs, profile=body.profile)
    state = run_pev(state)
    if not state.final:
        raise HTTPException(status_code=500, detail={"verify": state.verify.model_dump() if state.verify else None})
    return state.final.model_dump()


