# Research: Backend Core System — Phase 1

**Branch**: `001-backend-core-system` | **Date**: 2026-06-22
**Status**: Confirmed — all decisions already documented

## Overview

All technical decisions for Phase 1 were pre-defined in the architecture plan
(README.md) and project constitution (.specify/memory/constitution.md). No
NEEDS CLARIFICATION items exist. This document confirms the choices and their
rationale.

## Decision Log

### 1. Database Engine: SQLite → Neon PostgreSQL

- **Decision**: SQLite for development, Neon PostgreSQL for production
- **Rationale**: ACID compliance, zero configuration for dev, serverless scaling
  for prod. Same schema works for both (minor dialect adjustments).
- **Alternatives considered**: Excel files (rejected — corruption risk, slow),
  MySQL (unnecessary complexity for this scale)

### 2. Product Code Model

- **Decision**: 5 flat codes — NUT, 10\*20, 6\*25, 6\*30, 10\*25
- **Rationale**: No aliases or mapping layers. Codes ARE the names. Prevents
  Gemini hallucination.
- **Alternatives considered**: NUT-STD/NUT-M10/BOLT- prefixes (rejected —
  excessive complexity, agent confusion)

### 3. Agent SDK: OpenAI Agents SDK 0.17+

- **Decision**: Single orchestrator agent with 10 merged function tools
- **Rationale**: Fewer tools (<12) reduce Gemini 2.5 Flash hallucination risk.
  Structured + NLP input in same tool. SQLiteSession for conversation memory.
- **Alternatives considered**: LangChain (overkill), custom loop (reinventing
  the wheel)

### 4. LLM: Gemini 2.5 Flash

- **Decision**: Gemini 2.5 Flash via OpenAI-compatible Chat Completions endpoint
- **Rationale**: Free/cheap, fast, supports function calling, Roman Urdu capable.
  No Responses API — uses `set_use_responses_by_default(False)`.
- **Alternatives considered**: GPT-4o (cost), Claude (not compatible with SDK)

### 5. Email: Google OAuth 2.0 + Gmail API

- **Decision**: OAuth PKCE flow, encrypted token storage (Fernet)
- **Rationale**: No SMTP credentials needed. Token refresh handled automatically.
  Father controls when emails are sent.

### 6. Auth: Google OAuth PKCE

- **Decision**: Anyone can login. FATHER_EMAIL env var gates write access.
- **Rationale**: Simple, no password management. Read-only access for family/manager.

### 7. PDF Generation: reportlab

- **Decision**: reportlab for payslip PDFs
- **Rationale**: Already in project, mature, no LaTeX dependency.

### 8. Excel Export: openpyxl

- **Decision**: openpyxl for payslip Excel + manager report Excel
- **Rationale**: Already in project, template-based, no Java dependency.

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Gemini hallucinates tool calls | Medium | 10 tools only, strict validation, confirmation before save |
| Excel file corrupt on crash | Low (SQLite) | Not applicable — Excel is export only, DB is primary |
| OAuth token expires mid-session | Low | Auto-refresh + clear re-auth message |
| Roman Urdu parsing wrong | Medium | Agent confirms before saving, father corrects via edit |
| SQLite concurrency issues | Low | Single-user system, WAL mode |

## Dependencies

| Dependency | Version | Source | Purpose |
|-----------|---------|--------|---------|
| openai-agents | >=0.17.4 | PyPI | Agent orchestration |
| fastapi | >=0.136.3 | PyPI | REST API |
| fastmcp | >=3.4.2 | PyPI | MCP server |
| openpyxl | >=3.1.5 | PyPI | Excel export |
| reportlab | >=4.5.1 | PyPI | PDF payslips |
| google-auth-oauthlib | >=1.4.0 | PyPI | OAuth |
| google-api-python-client | >=2.197.0 | PyPI | Gmail API |
| uvicorn | >=0.49.0 | PyPI | ASGI server |
| apscheduler | >=3.11.2 | PyPI | Reminders |
| cryptography | >=48.0.1 | PyPI | Token encryption |
| python-dotenv | >=1.2.2 | PyPI | Env vars |
| python-multipart | >=0.0.32 | PyPI | Form data |
| jinja2 | >=3.1.6 | PyPI | Templating |
| httpx | >=0.28.1 | PyPI | HTTP client |
