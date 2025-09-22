# ARAM Coach — Patch-Scoped, Fact-Grounded LoL Agent (Local, LangGraph PEV)

Local-first ARAM strategy assistant with deterministic ThreatScore + LLM strategy, orchestrated via a LangGraph Plan → Evidence → Verify loop. Facts are loaded from local mock JSON (swap to Postgres later).

## Quickstart

1) Install uv (if not installed):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2) Sync deps and run the API:

```bash
uv sync
uv run serve
```

3) Explore docs: http://localhost:8000/docs

## Endpoints

- POST `/pre_game_advice`
- POST `/ingame_qa`

## Notes

- Uses mock data under `data/patches/14.99/` for champions, items, runes, and ARAM guide snippets.
- LangGraph state machine is defined in `app/graph.py`.
- Swap the mock JSON DB for Postgres DDragon ETL later.
- Use `uv run test` to run the test suite.

