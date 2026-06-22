# Tasks: Agent Core Optimizations

**Input**: Design documents from `specs/002-agent-core-optimizations/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tools.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Path Conventions

- Single project at repository root
- Existing files modified: `agent_system/orchestrator.py`, `agent_system/memory_manager.py`, `tools/database.py`, `config.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — no new files needed, all changes are in existing files

- [x] T001 [P] Add `ModelRouter` class with keyword-based complexity classification in `config.py`
- [x] T002 [P] Add thread-local connection cache in `tools/database.py` — replace `get_db()` with caching version using `threading.local()`
- [x] T003 [P] Add Pydantic `ProductionEntry` model with `worker`, `product_code`, `quantity` fields at top of `agent_system/orchestrator.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Changes that MUST be complete before any user story can be verified

- [x] T004 Token-based `compact_if_needed()` method in `agent_system/memory_manager.py` — implement `_estimate_tokens()`, `compact_if_needed()` with `MAX_TOKENS_ESTIMATE=8000`, preserve first + last 6 items

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Multi-Instruction Efficient Execution (Priority: P1) 🎯 MVP

**Goal**: Agent switches from `stop_on_first_tool` to `run_llm_again` with `parallel_tool_calls=True`, enabling concurrent tool execution in a single turn with natural language result processing.

**Independent Test**: Send "Kaleem ne 300 NUT aur 150 10*20 kiye, Sajjad ko absent karo, aur aaj ka status do" — verify all 3 instructions complete in ≤2 LLM turns with human-readable results.

### Implementation for User Story 1

- [x] T005 [US1] Update `_create_agent()` in `agent_system/orchestrator.py` — change `tool_use_behavior` to `"run_llm_again"`, add `parallel_tool_calls=True` to `ModelSettings`
- [x] T006 [US1] Update dynamic instructions in `agent_system/orchestrator.py` — remove "Do NOT generate text — only tool calls" rule, add instruction that LLM should process tool results and generate human-readable confirmations

**Checkpoint**: US1 fully functional — multi-instruction messages execute in parallel with natural language responses

---

## Phase 4: User Story 2 — Complexity-Based Model Routing (Priority: P2)

**Goal**: Simple queries route to lightweight model, complex queries use primary model, with automatic fallback on rate limits.

**Independent Test**: Send "aj ka status kya hai" — verify lightweight model selected. Send "June 2026 ki payslip banao" — verify primary model selected.

### Implementation for User Story 2

- [x] T007 [US2] Integrate `ModelRouter.select()` into `chat()` function in `agent_system/orchestrator.py` — use selected model as first attempt, fall through remaining chain on rate-limit errors
- [x] T008 [US2] Update `chat()` to call `memory.compact_if_needed()` after every successful turn in `agent_system/orchestrator.py`

**Checkpoint**: US2 functional — model selection varies by query complexity, auto-fallback works

---

## Phase 5: User Story 3 — Batch Daily Update (Priority: P2)

**Goal**: Composite `batch_daily_update_tool` handles production entries + absent workers in a single tool call with robust error handling.

**Independent Test**: Call batch tool with "[{"worker":"Kaleem","product_code":"NUT","quantity":300}]" and absent_workers '["Sajjad"]' — verify all records saved in one execution.

### Implementation for User Story 3

- [x] T009 [US3] Implement `batch_daily_update_tool()` function in `agent_system/orchestrator.py` — takes `entries_json` (str) and `absent_workers` (optional str), calls `log_production_json()` and `prod_mark_absent()`, returns combined results with error handling for each operation independently
- [x] T010 [US3] Add `batch_daily_update_tool` to `_create_agent()` tool list and add tool execution rule #11 in dynamic instructions in `agent_system/orchestrator.py`

**Checkpoint**: US3 functional — batch operations process in single tool call

---

## Phase 6: User Story 4 — Auto-Compacting Memory (Priority: P3)

**Goal**: Conversation memory auto-compacts after turns when token estimate exceeds threshold, maintaining consistent response times for long sessions.

**Independent Test**: Run 20+ conversation turns — verify auto-compaction triggers and response times stay consistent. Check with `/memory status`.
Note: Auto-compaction integration already done in T008 (chat function). This phase focuses on making it observable.

**Implementation for User Story 4**

- [x] T011 [US4] Update `/memory status` command in `main.py` to display estimated token count alongside item count in the interactive agent mode
- [x] T012 [US4] Update `/memory compact` in `main.py` and `memory_manager.py` to use the new token-based `compact_if_needed()` logic instead of the old fixed-count approach

**Checkpoint**: US4 functional — memory auto-manages, `/memory status` shows token count

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation updates

- [x] T013 Update `specs/002-agent-core-optimizations/quickstart.md` with final implementation details and testing instructions
- [x] T014 Run full verification — start agent, execute all user story tests, verify zero regressions in existing production/rejection/advance/payslip/email flows

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001, T002, T003 — all parallel, no dependencies
- **Foundational (Phase 2)**: T004 depends on Phase 1 completion
- **User Stories (Phase 3-6)**:
  - US1 (Phase 3) depends on Phase 1 + 2
  - US2 (Phase 4) depends on T001 (ModelRouter class) + T005 (chat function updated)
  - US3 (Phase 5) depends on Phase 1 + 2 — independent of US1/US2/US4
  - US4 (Phase 6) depends on T004 (compact method) + T008 (auto-compact in chat)
- **Polish (Phase 7)**: Depends on all user stories complete

### Parallel Opportunities

| Task IDs | Why |
|----------|-----|
| T001, T002, T003 | Different files, no dependencies |
| T005, T007, T009 | Different concerns, can be implemented by different developers |
| T011, T012 | Different files (main.py vs memory_manager.py), no dependencies |

### Within Each User Story

- T005 (model settings) → T006 (instructions) — sequential, same file
- T007 (ModelRouter integration) → T008 (auto-compact in chat) — sequential, same function
- T009 (batch tool) → T010 (tool list + instructions) — sequential, same file
- T011 (memory status) → T012 (memory compact) — parallel, different files

---

## Parallel Example: User Story 1, 2, 3

```bash
# Launch US1 + US2 + US3 together (different concerns, different parts of orchestrator.py):
Task: "T005 Update _create_agent() in agent_system/orchestrator.py"
Task: "T007 Integrate ModelRouter into chat() in agent_system/orchestrator.py"
Task: "T009 Implement batch_daily_update_tool in agent_system/orchestrator.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004)
3. Complete Phase 3: User Story 1 (T005-T006)
4. **STOP and VALIDATE**: Send multi-instruction message — verify parallel execution
5. If stable, deploy/demo

### Incremental Delivery

1. Setup + Foundational → Core infrastructure ready
2. Add US1 (run_llm_again + parallel) → MVP — deploy/demo
3. Add US2 (ModelRouter) → Cost savings — deploy/demo
4. Add US3 (Batch tool) → Efficiency — deploy/demo
5. Add US4 (Auto-compact) → Production readiness — deploy
6. Polish → Final verification

### Single-Developer Order

```
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014
```

### Parallel Team Strategy

With multiple developers:

1. Developer A: T001 (ModelRouter class) + T002 (DB cache) + T003 (Pydantic)
2. Developer B: T004 (Memory) + T011 (status) + T012 (compact)
3. Once Phase 1+2 done:
   - Dev A: T005 + T006 (US1) → T007 + T008 (US2)
   - Dev B: T009 + T010 (US3)
4. Polish: T013 + T014 together

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each logical group of tasks
- All four user stories can be verified without affecting each other
- T014 run all manual tests before marking feature complete
