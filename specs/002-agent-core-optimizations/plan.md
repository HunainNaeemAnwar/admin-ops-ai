# Implementation Plan: Agent Core Optimizations

**Branch**: `002-agent-core-optimizations` | **Date**: 2026-06-22 | **Spec**: specs/002-agent-core-optimizations/spec.md
**Input**: Feature specification from specs/002-agent-core-optimizations/spec.md

## Summary

Optimize the orchestrator agent's core execution path: switch from `stop_on_first_tool` to `run_llm_again` with parallel tool calls, add a composite batch tool, implement ModelRouter for complexity-based model selection, add token-based auto-compaction for conversation memory, and add thread-local database connection caching. All changes are purely backend refactoring with zero impact on user-facing functionality.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: openai-agents >=0.17.4, sqlite3 (stdlib), pydantic  
**Storage**: SQLite (no schema changes)  
**Testing**: pytest + manual agent conversation tests  
**Target Platform**: Linux server (CLI + FastAPI web)  
**Project Type**: single (Python monolith)  
**Performance Goals**: Multi-instruction messages in ≤2 LLM turns, simple queries in ≤2 seconds  
**Constraints**: Zero regressions in existing production/absent/rejection/advance/payslip/email flows  
**Scale/Scope**: Single-user factory tracking system, 8 workers, single father operator

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Assessment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Father-Triggered Control | ✅ PASS | No auto-execution added. Father still triggers everything. |
| II. Manager Reporting | ✅ PASS | No changes to reporting pipeline. |
| III. Database-First Persistence | ✅ PASS | SQLite remains primary. Thread-local cache is an optimization, not a storage change. |
| IV. Complete Daily Tracking | ✅ PASS | Not affected by any change. |
| V. Simple Product Model | ✅ PASS | Not affected. |
| VI. Auth & Access Control | ✅ PASS | Not affected. |

All constitutional gates pass. No violations.

### Post-Design Re-check

✅ All gates remain passing. No design decisions violate constitutional principles.

## Project Structure

### Documentation (this feature)

```text
specs/002-agent-core-optimizations/
├── plan.md              # This file
├── research.md          # Phase 0 — research findings
├── data-model.md        # Phase 1 — entity contracts (logical, no new DB tables)
├── quickstart.md        # Phase 1 — updated setup guide
├── contracts/           # Phase 1 — tool interface contracts
└── tasks.md             # Phase 2 — task breakdown
```

### Source Code (repository root)

No new source files. All changes modify existing files:

```text
agent_system/
├── orchestrator.py      # run_llm_again, parallel_tool_calls, batch tool, ModelRouter
└── memory_manager.py    # Token-based auto-compaction

tools/
└── database.py          # Thread-local connection cache

config.py                # ModelRouter class
```

**Structure Decision**: Pure refactoring — existing file modifications only. No new directories or entry points.

## Complexity Tracking

No constitutional violations. Complexity tracking not required.
