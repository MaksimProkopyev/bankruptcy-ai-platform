# agents/

LangGraph-based AI agents for the bankruptcy platform.

Package layout

```
agents/
├── shared/                 # cross-agent infrastructure
│   ├── llm_router.py       # YandexGPT (152-ФЗ) vs Claude Sonnet routing
│   └── checkpointer.py     # AsyncPostgresSaver factory
└── qualification/          # first-touch lead-qualification graph
    ├── state.py            # QualificationState (TypedDict)
    ├── config.py           # retry windows, score thresholds, URLs
    ├── prompts.py          # Russian system prompts (per node)
    ├── nodes.py            # async node implementations
    ├── edges.py            # conditional-edge functions
    └── graph.py            # StateGraph wiring + compile
```

## Qualification agent

### LLM routing (152-ФЗ compliant)

| Node                  | Model           | Why                                  |
| --------------------- | --------------- | ------------------------------------ |
| `greet`               | YandexGPT Pro   | sends/processes PII (RU perimeter)   |
| `ask_next_question`   | YandexGPT Pro   | "                                    |
| `process_reply`       | YandexGPT Pro   | "                                    |
| `extract_signals`     | YandexGPT Pro   | parses raw chat                      |
| `detect_conflicts`    | Claude Sonnet 4 | reasoning over anonymised signals    |
| `resolve_conflicts`   | Claude Sonnet 4 | "                                    |
| `assess_eligibility`  | Claude Sonnet 4 | ФЗ-127 logic                         |
| `score_lead`          | Claude Sonnet 4 | numerical scoring                    |
| `retry_message`       | YandexGPT Lite  | short template reply                 |
| `disqualify`          | YandexGPT Lite  | short template reply                 |

### Graph (high level)

```
START → greet → ask_next_question → wait_for_reply
                                       ├─ inbound  → process_reply
                                       │              ├─ queue not empty → ask_next_question
                                       │              └─ queue empty     → extract_signals
                                       └─ timeout → retry_message
                                                      ├─ < max retries → ask_next_question
                                                      ├─ esc=0         → soft_escalate
                                                      ├─ esc=1         → hard_escalate (interrupt)
                                                      └─ otherwise     → archive

extract_signals → detect_conflicts
                    ├─ has conflicts → resolve_conflicts → wait_for_reply
                    └─ no conflicts  → assess_eligibility → score_lead
                                                              ├─ >70  → create_prospect → END
                                                              ├─ <36  → disqualify       → END
                                                              └─ 36..70 → soft_escalate  → wait_for_reply
```

Notes
- `wait_for_reply` and `hard_escalate` rely on LangGraph `interrupt_before`/
  `NodeInterrupt` so the graph can be paused and resumed via the Postgres
  checkpointer (`shared/checkpointer.py`).
- `create_prospect`, `disqualify`, `archive` issue HTTP calls to the backend
  (`/api/v1/internal/prospects`) and leadgen (`/api/v1/ai/qualification-result`)
  services. URLs and secrets come from env (`BACKEND_URL`, `LEADGEN_URL`,
  `INTERNAL_SECRET`).
- This package only defines and compiles the graph; orchestration (channel
  ingestion, message dispatch, scheduling retries) lives elsewhere.

## Required env

```
DATABASE_URL=postgresql://...        # for the checkpointer
YANDEX_API_KEY=...
YANDEX_FOLDER_ID=...
ANTHROPIC_API_KEY=...
BACKEND_URL=http://backend:8000
LEADGEN_URL=http://leadgen:8002
INTERNAL_SECRET=...                  # X-Internal-Secret for backend
```

## Install

```
pip install -r agents/requirements.txt
```

## Smoke check

```
python -c "from agents.qualification.graph import build_qualification_graph; print('OK')"
```
