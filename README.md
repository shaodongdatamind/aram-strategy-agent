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

Optional: set your OpenAI API key for LLM features

1) Create a file `.secrets/openai_api_key` with your key:

```
mkdir -p .secrets
echo "sk-..." > .secrets/openai_api_key
```

Or set an environment variable before running:

```
export OPENAI_API_KEY="sk-..."
```

If you use `run.sh`, it will auto-load `.env` and `.secrets/openai_api_key` if present.

3) Explore docs: http://localhost:8000/docs

## Endpoints

- POST `/pre_game_advice`
- POST `/ingame_qa`

## Notes

- Uses mock data under `data/patches/14.99/` for champions, items, runes, and ARAM guide snippets.
- LangGraph state machine is defined in `app/graph.py`.
- Swap the mock JSON DB for Postgres DDragon ETL later.
- Use `uv run test` to run the test suite.

### Execution Graph (Plan → Evidence → Verify)

```
Client Input (HTTP/CLI)
   │
   ▼
build_initial_state(patch, inputs)
   │  AgentState
   ▼
node_retrieve ──> facts = {items, champs, runes, guides}
   │
   ▼
node_retrieval_agent ──> retrieval.snippets ← BM25 over guides
   │
   ▼
node_threat ──> threat.scores (simple heuristic for now)
   │
   ▼
node_strategy ──> draft (role, build_plan, tldr, evidence)
   │
   ▼
node_guardrail ──> verify (violations?) ──┐
   │                                     │ if not ok, re-plan (limited loops)
   │                                     └───────────────┐
   ▼                                                     │
final (StrategyFinal)  ◄─────────────────────────────────┘
```

See `app/graph.py` for the node functions and control flow.

