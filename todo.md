# ARAM Coach — Project TODO (Local, LangGraph, PEV)

## Legend
- [ ] Not started
- [~] In progress
- [x] Done

---

## M0 — Repo & Scaffolding
- [ ] Monorepo layout: `apps/api`, `core/{schemas,data_access,etl,retrieval,reasoning,generation,personalization}`, `orchestration/graph`, `infra`, `tests`
- [ ] `DESIGN.md` (planning review) + `POLICY.yaml` (ARAM-only rules, item tag defs)
- [ ] FastAPI app skeleton: `/health`, `/pre_game_advice`, `/ingame_qa`
- [ ] Settings: `.env`, pydantic-settings; logging config
- [ ] CI: ruff/black/mypy + pytest + coverage

## M1 — Data & DB (Patch-Scoped)
- [ ] Postgres DDL (partition by `patch`): `item`, `champion`, `rune`, `aram_guide_card`, `patch_change_log`
- [ ] Item functional tags: `GrievousWounds`, `AntiShield`, `ArmorPen`, `MagicPen`, `Tenacity`, `HealAmp` (+ tests)
- [ ] ETL: DDragon `versions.json` → resolve latest patch
- [ ] ETL: load `items.json`, `champion.json`, `runes` → Postgres
- [ ] Diff → `patch_change_log` with before/after values
- [ ] Indexes: `(patch,name)` btree; tags GIN; pgvector for guides
- [ ] Seed **mock patch** dataset for tests (2 champs, ~10 items, 5 guide snippets)

## M2 — Retrieval & Evidence
- [~] BM25 over `aram_guide_card` (baseline in-memory rank-bm25; prod backend TBD)
- [ ] Embeddings + pgvector; `vector_search()`, `bm25_search()`, `rerank()`
- [ ] Retrieval router: fact queries → SQL; strategy queries → hybrid+rerank
- [ ] Evidence packer: `retrieval.snippets` with provenance (ids, patch)
- [ ] LLM reranker/query-rewriter for guide snippets (constrained to snippet ids)

## M3 — Agents & Schemas (PEV)
- [x] Pydantic: `AgentState`, `ItemRow`, `ChampRow`, `RuneRow`, `Snippet`, `StrategyDraft`, `StrategyFinal`, `Violation`
- [ ] **FactsAgent**: SQL-only tools; returns rows; unit tests
- [ ] **RetrievalAgent**: hybrid retrieval; returns snippets; unit tests (Recall@K/NDCG on mock)
- [~] **ThreatAgent** v0: deterministic scoring; unit tests
- [ ] **StrategyAgent** (LLM): prompt + JSON schema + deterministic fallback; tests
- [~] **GuardrailAgent**: policies (patch consistency, ARAM scope, stat parity, TL;DR ≤3); tests per policy
- [ ] **RefineStrategy**: violation-aware re-prompt; retry cap; tests
- [ ] LLM Guardrail judge: factuality/style critique → suggestions (PEV re-plan)

## M4 — LangGraph Orchestration
- [ ] Define `AgentState` store & checkpointer (filesystem/sqlite)
- [ ] Nodes: `RetrieveGameData` → `RetrievalAgent` → `ThreatAgent` → `StrategyAgent` → `GuardrailAgent` → [conditional] `RefineStrategy`
- [ ] Edges: PEV loop with max attempts (1–2)
- [ ] Replay hooks + trace logging per node (dev mode)
- [ ] E2E tests: basic / one-loop refine / edge inputs; assert node order & final schema

## M5 — API Wiring
- [x] `/pre_game_advice` request/response schemas; validation & errors
- [x] `/ingame_qa` request/response schemas; validation & errors
- [x] Response composer: `{tldr, assumptions, threats, role, build_plan, evidence, patch}`
- [~] Error paths: “DDragon not updated for patch X”, missing data, etc.

## M6 — LLM Runtime (Local)
- [ ] Ollama or vLLM integration; config for temperature=0 & seed for tests
- [ ] Optional API router (OpenRouter) with kill-switch
- [ ] Retries on schema failure; cost/latency logging

## M7 — Quality, Caching, Observability
- [ ] Fact accuracy tests (random item/skill facts vs SQL rows)
- [ ] Patch consistency checker (random prompts in CI)
- [ ] Redis cache for hot patches/queries (optional)
- [ ] Prometheus metrics; structured logs per node; minimal trace UI page

## Backlog / Nice-to-Have
- [ ] Multilingual output parity (zh-CN/zh-TW/en) with identical facts
- [ ] Guide distillation job (auto-generate ARAM cards per champ)
- [ ] A/B re-rankers; latency budget tests
- [ ] Desktop overlay adapter (Overwolf/Live Client Data)
- [ ] Spectator client (active roster) with opt-in auth

## Done
- [ ] (move tasks here)
