# Implementation Plan: Backend Core System — Phase 1

**Branch**: `001-backend-core-system` | **Date**: 2026-06-22 | **Spec**: [spec.md](../spec.md)
**Input**: Feature specification from `/specs/001-backend-core-system/spec.md`

## Summary

Implement the complete Phase 1 backend for the factory piece-rate worker tracking
system. This covers: SQLite database schema (6 tables), 10 merged function tools
for the Gemini 2.5 Flash agent, Roman Urdu NLP for production recording, rejection
distribution system, advance payment tracking, absent marking, PDF+Excel payslip
generation, manager reporting (quantities-only email + Excel exports), Google OAuth
with FATHER_EMAIL gate, and CLI agent interface. All based on the architecture plan
in README.md and the project constitution.

Father (contractor) controls the agent via Roman Urdu chat. No auto-execution
anywhere — every action is father-triggered.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, FastMCP, OpenAI Agents SDK 0.17+, openpyxl,
  reportlab, google-auth-oauthlib, google-api-python-client, APScheduler,
  python-dotenv, uvicorn, python-multipart, cryptography, httpx
**Storage**: SQLite (dev) → Neon PostgreSQL (prod)
**Testing**: pytest (unit + integration)
**Target Platform**: Linux server (CLI + HTTP API)
**Project Type**: Single Python backend project (CLI agent + FastAPI + MCP server)
**Performance Goals**: Payslips for all 8 workers < 10s, queries < 1s
**Constraints**: Father-triggered only — no auto-execution. 8 fixed workers.
  5 simple product codes. Plain-text email only. Excel for export only.
**Scale/Scope**: 1 primary user (father) + read-only family/manager. Single-machine
  deployment. 30 days × 8 workers × 5 products = ~1200 daily_log rows/month.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Father-Triggered Control | ✅ PASS | No auto-email/auto-payslip anywhere. Father triggers all. |
| II. Manager Reporting Constitution | ✅ PASS | Quantities-only, no individual/financial data. Excel attachments. |
| III. Database-First Persistence | ✅ PASS | SQLite primary, Excel only for export. 6 required tables. |
| IV. Complete Daily Tracking | ✅ PASS | Every worker×day has data or absent. Agent enforces. |
| V. Simple Product Model | ✅ PASS | Exactly 5 codes (NUT, 10\*20, 6\*25, 6\*30, 10\*25). |
| VI. Auth & Access Control | ✅ PASS | FATHER_EMAIL gate. Read-only for others. |

**No violations.** Complexity tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/001-backend-core-system/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 — research & decisions
├── data-model.md        # Phase 1 — data model & schema
├── quickstart.md        # Phase 1 — getting started guide
├── contracts/           # Phase 1 — API contracts
│   ├── database.md      # DB schema contract
│   ├── tools.md         # Tool signatures contract
│   └── endpoints.md     # REST endpoint contracts
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
admin-ops-ai/
├── main.py                   # Entry point: agent | web | mcp | scheduler
├── config.py                 # Env vars, paths, constants
├── seed.py                   # Database seed (workers + products)

├── agent_system/
│   ├── __init__.py
│   ├── provider.py           # Gemini endpoint config
│   ├── orchestrator.py       # Agent with 10 tools, memories, chat()
│   ├── memory_manager.py     # ConversationMemory (SQLiteSession)
│   ├── data_extractor.py     # NLP extraction from Roman Urdu
│   └── email_agent.py        # AI email composer

├── tools/
│   ├── __init__.py
│   ├── database.py           # SQLite/PostgreSQL CRUD (core)
│   ├── production_tools.py   # log_production, mark_absent, update_entry
│   ├── rejection_tools.py    # log_rejection, distribution logic
│   ├── advance_tools.py      # record_advance, deduction calc
│   ├── report_tools.py       # get_daily_status, get_summary
│   ├── email_tools.py        # Gmail API send (dept-only reports)
│   ├── oauth_tools.py        # Google OAuth PKCE
│   ├── payslip_tools.py      # PDF + Excel payslip export
│   └── export_tools.py       # Excel export for manager reports

├── web_ui/
│   ├── routes.py             # FastAPI routes
│   ├── static/
│   └── templates/

├── data/                     # Runtime data (git-ignored)
│   ├── accounts.db           # SQLite database
│   ├── agent_memory/         # Conversation memory
│   ├── pay_slips/            # Generated payslips
│   └── tokens/               # OAuth tokens

├── mcp_server.py             # FastMCP server (10 tools)
├── scheduler.py              # APScheduler (reminders only)
├── template.xlsx             # Excel export template
└── tests/                    # Test directory
    ├── test_database.py
    ├── test_tools.py
    └── test_agent.py
```

**Structure Decision**: Single Python project — the existing structure is already
well-organized. New `tools/database.py` replaces the old `tools/excel_tools.py` as
the primary data layer. Excel management moves to `tools/export_tools.py`.

## Complexity Tracking

> No violations found. No complexity tracking needed.

## Phase 0: Outline & Research

### Research Tasks

All technical decisions are already documented in README.md and the constitution.
No NEEDS CLARIFICATION items exist. Research is limited to confirming existing
choices.

| Topic | Decision | Source |
|-------|----------|--------|
| Database engine | SQLite (dev) → Neon PostgreSQL (prod) | Constitution III |
| Product codes | NUT, 10\*20, 6\*25, 6\*30, 10\*25 | Constitution V |
| Agent SDK | OpenAI Agents SDK 0.17+ | Constitution Tech Stack |
| LLM | Gemini 2.5 Flash (OpenAI-compatible) | Constitution Tech Stack |
| Email | Google OAuth 2.0 + Gmail API | Constitution Tech Stack |
| Auth | Google OAuth PKCE | Constitution VI |
| PDF | reportlab | Constitution Tech Stack |
| Excel export | openpyxl | Constitution Tech Stack |

## Phase 1: Design & Contracts

### Data Model

See `data-model.md` for full schema. 6 core tables:

1. `workers` — 8 fixed workers
2. `products` — 5 items with rates
3. `daily_log` — worker × product × day
4. `rejections` — department-level monthly rejection
5. `advances` — per-worker advances
6. `payslips` — cached monthly summaries

### API Contracts

| Action | User Says | Tool Called | Data Written |
|--------|-----------|-------------|-------------|
| Record work | "Aj Kaleem ne 300 nut kiye" | `log_production` | `daily_log` |
| Mark absent | "Kashif ki chutti thi" | `mark_absent` | `daily_log.is_absent` |
| Record rejection | "June main 1000 nut reject" | `log_rejection` | `rejections` |
| Record advance | "Kaleem ko 2000 advance" | `record_advance` | `advances` |
| Get daily total | "Aj k total kitna hua?" | `get_daily_status` | Read `daily_log` |
| Get summary | "June ka summary do" | `get_summary` | Read all tables |
| Generate payslip | "Sab ki payslip banao" | `generate_payslip` | Read all, write `payslips` |
| Edit entry | "300 nut ko 500 kr do" | `update_entry` | Update `daily_log` |
| Send report | "Manager ko email bhejo" | `send_report` | Read `daily_log`, send email |
| List catalog | - | `list_catalog` | Read `workers` + `products` |

### REST Endpoints (FastAPI)

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/` | Dashboard | Anyone |
| GET | `/login` | Google OAuth login | None |
| GET | `/oauth/callback` | OAuth callback | None |
| POST | `/chat` | Agent chat message | FATHER_EMAIL |
| GET | `/daily` | Daily summary (JSON) | Anyone |
| GET | `/monthly` | Monthly summary (JSON) | Anyone |
| GET | `/workers` | List workers | Anyone |
| GET | `/worker/{name}` | Worker detail | Anyone |
| GET | `/products` | Product catalog | Anyone |
| PUT | `/products/{code}` | Update product rate | FATHER_EMAIL |

### Quickstart

See `quickstart.md` for setup guide.

### Agent Context

Update `.opencode/` or agent-specific context files with new tool signatures
and behavioral rules after implementation.

## Phase 2: Tasks (Next — /sp.tasks)

TBD — will be created via `/sp.tasks` command.

Tasks will be organized by user story:

- **Phase A: Foundation** — database schema, config, seed
- **Phase B: US1** — production recording tools + agent
- **Phase C: US2** — rejection, advance, absent tools
- **Phase D: US3** — payslip generation
- **Phase E: US4** — email reports
- **Phase F: US5** — auth & access control
- **Phase G: Integration** — CLI agent, web routes, testing
