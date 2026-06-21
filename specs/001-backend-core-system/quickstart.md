# Quickstart: Backend Core System — Phase 1

**Branch**: `001-backend-core-system` | **Date**: 2026-06-22

## Prerequisites

- Python 3.12+
- UV package manager (`pip install uv` or standalone)
- Gemini API key
- Google Cloud OAuth credentials (for email)

## Setup

```bash
# 1. Clone and enter project
git clone <repo-url>
cd admin-ops-ai

# 2. Create virtual environment and install deps
uv venv
source .venv/bin/activate
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env with your values (see below)

# 4. Seed database
python seed.py
```

## Environment (.env)

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

MANAGER_EMAIL=manager@company.com
FATHER_EMAIL=hunainnaeemanwar@gmail.com

GMAIL_CLIENT_ID=your_oauth_client_id
GMAIL_CLIENT_SECRET=your_oauth_client_secret
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email openid
GMAIL_REDIRECT_URI=http://localhost:8000/oauth/callback
FRONTEND_URL=http://localhost:3000

RATE_NUT=1.0
RATE_10X20=2.0
RATE_6X25=1.5
RATE_6X30=2.5
RATE_10X25=1.75

TAX_PERCENTAGE=3.0

FIXED_WORKERS=Naeem,Kaleem,Akbar,Suny,Sajjad,Irfan,Kashif,Gulmast

DATABASE_URL=sqlite:///data/accounts.db
```

## Running

```bash
# CLI Chat Agent (Primary Interface)
python main.py agent

# Web UI (FastAPI Dashboard)
python main.py web

# MCP Server (for external agent integration)
python main.py mcp

# Scheduler (reminders only)
python main.py scheduler
```

## First-Time Usage

1. Start the agent: `python main.py agent`
2. The agent will greet you and check if today has data
3. Tell the agent in Roman Urdu: "Aj Kaleem ne 300 nut kiye"
4. Agent confirms and shows summary
5. Continue adding data for all workers
6. At month end: "Sab ki payslip banao"
7. To email manager: "Manager ko daily email bhejo"

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point |
| `config.py` | Environment config |
| `seed.py` | Database seeding |
| `tools/database.py` | Database CRUD |
| `tools/production_tools.py` | Production logging tools |
| `tools/rejection_tools.py` | Rejection recording |
| `tools/advance_tools.py` | Advance tracking |
| `tools/report_tools.py` | Summary/report tools |
| `tools/email_tools.py` | Gmail API send |
| `tools/oauth_tools.py` | Google OAuth flow |
| `tools/payslip_tools.py` | PDF + Excel payslip |
| `tools/export_tools.py` | Excel report export |
| `agent_system/orchestrator.py` | AI agent with 10 tools |
| `agent_system/data_extractor.py` | Roman Urdu NLP |
| `mcp_server.py` | FastMCP server |
| `web_ui/routes.py` | FastAPI routes |
