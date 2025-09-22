# Comprehensive Planning Audit for the ARAM AI Agent System

## Architectural Plan Validation and Refinement

The current plan for the League of Legends ARAM AI Agent breaks the problem into logical components (data retrieval, strategy generation, output filtering), which is a sound approach. Decomposing the system into specialized sub-agents aligns with best practices in multi-agent architecture: complex tasks are easier to manage when divided among focused modules. This modular design also improves maintainability and scalability.

### Recommended Module Definitions

- **Data Ingestion/Retrieval**  
  Loads relevant game data (champion stats, item details, patch notes) from local files or databases. Outputs a structured context object with all necessary facts for ARAM mode.

- **StrategyAgent (Planning)**  
  An LLM-powered agent that produces a structured or free-form strategic plan. The output schema must be clearly defined for later validation.

- **GuardrailAgent (Output Filter)**  
  A rule-based or LLM-based checker that ensures adherence to content guidelines and correctness rules. It validates structure, style, and factual accuracy.

- **Orchestrator**  
  A controller (e.g. LangGraph) that sequences steps, manages state, and implements a Plan–Execute–Verify cycle.

### Key Refinements

- Explicitly define each component’s contract (inputs, outputs).  
- Add factual verification of strategy output.  
- Handle errors gracefully (missing data, timeouts).  
- Ensure local-first deployment (local LLM, vector DBs, JSON/SQLite storage).  
- Add caching for embeddings and outputs.

---

## LangGraph-Oriented System Design

LangGraph reframes the agent system as a **state machine** with nodes and edges controlling execution.

### Example Nodes

- **RetrieveGameData**: Updates state with champion info, items, and patch updates.  
- **GenerateStrategy**: Invokes LLM to propose a draft strategy.  
- **VerifyStrategy**: Checks draft for policy compliance, factual correctness, and completeness.  
- **End/Output**: Formats and returns final strategy.

### PEV Loop (Plan–Execute–Verify)

- Flow: RetrieveGameData → GenerateStrategy → VerifyStrategy → (end or loop).  
- Verification may trigger refinement loops with feedback integrated into prompts.  
- Upper bound on retries prevents infinite cycles.  
- State includes counters, verdicts, and feedback.  

### Debugging Benefits

- State logging and persistence (e.g. SQLite backend).  
- Replayable sessions and step-by-step debugging.  
- Visualization in LangGraph Studio.  
- Human-in-the-loop checkpoints possible during development.

### Testability

- Nodes are unit-testable with state snapshots.  
- Explicit state machine ensures transparent control flow.  

---

## Testing and Evaluation Framework

Testing an LLM-driven agent requires a mix of unit tests, scenario-based evaluations, and automated metrics.

### Testing Layers

1. **Unit Tests**: For retrieval, generation, guardrail enforcement.  
2. **Integration Tests**: Full end-to-end flows with PEV loop.  
3. **Evaluation Metrics**: Information retrieval (Recall@K, NDCG), schema compliance, output quality.

### Success Criteria

- Schema adherence.  
- Presence of key content.  
- Compliance with rules.  
- Alignment with “ideal” test trajectories.

---

## Output Schema Validation

- Define schema with **Pydantic** or **JSON Schema**.  
- Validate LLM outputs strictly.  
- GuardrailAgent integrates schema validation.  
- Unit tests include malformed vs. valid outputs.  

---

## Mock Data for Patches, Champions, and Items

- Use dummy datasets (e.g. Ahri, Garen) with simplified stats and patch notes.  
- Ensures deterministic, offline tests.  
- Enables targeted regression scenarios.  
- Supports robust edge-case testing (nonexistent champions, missing data).  

---

## Retrieval Component Evaluation (Recall@K, NDCG)

- Define ground truth relevant documents for test queries.  
- Evaluate Recall@K (coverage) and NDCG (ranking quality).  
- Test failure modes (nonexistent champions, broad queries).  
- Ensure robustness and high-quality context retrieval.  

---

## StrategyAgent Output Correctness

- **Schema & Content Checks**: Ensure mention of key items, ability orders, and advice.  
- **Factual Consistency**: Cross-check against mock data to prevent hallucinations.  
- **Consistency Across Runs**: Use fixed seeds or mock outputs for regression tests.  
- **Golden Path Scenarios**: Define expected outcomes for champion-specific queries.  

---

## GuardrailAgent Policy Enforcement

- **Content Moderation**: Remove toxicity.  
- **Schema Enforcement**: Fix formatting issues.  
- **Factual Checks**: Flag contradictions with mock data.  
- **Style Enforcement**: Enforce tone and phrasing rules.  

---

## End-to-End Flow Testing (PEV Loop)

- **Basic Scenario**: Strategy generation for a champion.  
- **Loop Scenario**: Missing elements trigger regeneration.  
- **Edge Scenario**: Unusual queries handled gracefully.  

Logs and replayable states support debugging. CI pipelines should run the full suite for regression prevention.

---

## Sources

- Mishra, S. *LangGraph: Simplifying Agent Orchestration and State Management*. Medium, 2025.  
- AWS Machine Learning Blog. *Build multi-agent systems with LangGraph and Amazon Bedrock*. 2025.  
- Sowft Blog. *ChemCrow and AI Agents with Guardrails*. 2025.  
- Galileo.ai Blog. *Unit Testing AI Systems*. 2025.  
- Pydantic.dev. *Validating Structured Outputs*. 2024.  
- Patronus AI Docs. *Unit Testing Agents*. 2023.  
- Google ADK Docs. *Why Evaluate Agents*. 2023.  
- EvidentlyAI. *NDCG Metric*. 2025.  
- Murugan, R. *LLM Evaluation Metrics: RAG, MRR, NDCG, ROUGE, BLEU*. Medium, 2024.  

---
