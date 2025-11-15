# ARAM Coach — Patch-Scoped, Fact-Grounded LoL Agent (Local, LangGraph PEV)

Local-first ARAM strategy assistant with LLM-powered threat scoring and strategy generation, orchestrated via a Plan → Evidence → Verify (PEV) loop. Facts are loaded from local JSON files (items, champions, runes), while guides and win rates are fetched at runtime from metasrc.com.

## Quickstart

1) Install uv (if not installed):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2) Sync deps and run the API:

```bash
# Option 1: Use run.sh (recommended - auto-loads .env and secrets)
./run.sh

# Option 2: Direct uvicorn command
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Required: Set your OpenAI API key for LLM features**

The application requires OpenAI API access for threat scoring and strategy generation. Create a file `.secrets/openai_api_key` with your key:

```bash
mkdir -p .secrets
echo "sk-..." > .secrets/openai_api_key
```

Or set an environment variable before running:

```bash
export OPENAI_API_KEY="sk-..."
```

If you use `run.sh`, it will auto-load `.env` and `.secrets/openai_api_key` if present.

3) Access the application:

- **Web UI**: http://localhost:8000/ (interactive interface)
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **OpenAPI Spec**: http://localhost:8000/openapi.json

## Endpoints

- `GET /` - Web UI (interactive HTML interface)
- `POST /pre_game_advice` - Get pre-game strategy advice
- `POST /ingame_qa` - Ask questions during gameplay

## Architecture

### Data Sources

- **Local JSON**: Patch-specific data (items, champions, runes) stored in `data/patches/{patch}/`
  - Default patch: `14.99` (configurable via `DEFAULT_PATCH` in `app/graph.py`)
  - Files: `items.json`, `champs.json`, `runes.json`
  - Use `scripts/fetch_ddragon.py` to fetch latest data from Data Dragon

- **Runtime Fetching**:
  - **ARAM Guides**: Fetched from metasrc.com at runtime for relevant champions (`app/guide.py`)
  - **Win Rates**: Live ARAM win rates from metasrc.com for threat scoring (`app/threat.py`)

### Execution Graph (Plan → Evidence → Verify)

```
Client Input (HTTP POST)
   │
   ▼
build_initial_state(patch, inputs)
   │  AgentState
   ▼
node_load_patch_facts ──> facts = {items, champs, runes}
   │
   ▼
node_search_guides ──> retrieval.snippets ← Fetched from metasrc.com
   │
   ▼
node_threat ──> threat.scores ← Live win rates + LLM analysis (1-10 scale)
   │
   ▼
node_strategy ──> draft (role, build_plan, tldr, evidence) ← LLM generation
   │
   ▼
node_guardrail ──> verify (violations?) ──┐
   │                                     │ if not ok, re-plan (max 1 loop)
   │                                     └───────────────┐
   ▼                                                     │
final (StrategyFinal)  ◄─────────────────────────────────┘
```

### Key Components

- **`app/main.py`**: FastAPI application with web UI and API endpoints
- **`app/graph.py`**: PEV orchestration (defines node execution order)
- **`app/db.py`**: Loads patch data from local JSON files
- **`app/guide.py`**: Fetches and extracts ARAM guides from metasrc.com
- **`app/threat.py`**: Computes threat scores using live win rates + LLM analysis
- **`app/strategy_agent.py`**: Generates strategies using OpenAI LLM
- **`app/guardrail.py`**: Validates outputs (TL;DR length, ARAM scope, item existence)
- **`app/llm.py`**: OpenAI client wrapper
- **`app/state.py`**: Pydantic models for all data structures

### Notes

- Default patch: `14.99` (found in `data/patches/14.99/`)
- LLM models used: `gpt-4o-mini` (configurable in `app/threat.py` and `app/strategy_agent.py`)
- PEV loop: Maximum 1 refinement attempt (`max_loops=1` in `run_pev`)
- Guardrail checks: TL;DR length (≤3), ARAM-only content, item existence validation
- Use `uv run test` to run the test suite

See `app/graph.py` for the node functions and control flow.

