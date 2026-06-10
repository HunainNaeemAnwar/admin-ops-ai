# Admin Ops AI — Multi-Agent Accountant System

Factory piece-rate worker tracking, daily wage calculation, Gmail reports, and monthly pay slips.

## Tech Stack

- **Python 3.14** via [UV](https://docs.astral.sh/uv/) package manager
- **OpenAI Agents SDK** — multi-agent orchestration with function tools
- **FastMCP** — MCP server for external agent integration
- **FastAPI** — web UI
- **Gemini** (via OpenAI-compatible endpoint) — LLM for chat agent
- **Google OAuth 2.0** — Gmail API email sending
- **openpyxl** — template-based monthly Excel reports

## Fixed Workers

| # | Worker |
|---|--------|
| 1 | Naeem  |
| 2 | Kaleem |
| 3 | Akbar  |
| 4 | Suny   |
| 5 | Sajjad |
| 6 | Irfan  |
| 7 | Kashif |
| 8 | Gulmast |

## Product Columns (Monthly Sheet)

| Column | Product Codes  | Rate  |
|--------|---------------|-------|
| NUT    | NUT-STD, NUT-M10 | Rs 1.0 / 1.2 |
| 10*20  | BOLT-10x20    | Rs 2.0 |
| 6*25   | BOLT-6x25     | Rs 1.5 |
| 6*30   | BOLT-6x30     | Rs 2.5 |
| 10*25  | BOLT-10x25    | Rs 1.75 |

## Setup

```bash
# 1. Create venv
uv venv
source .venv/bin/activate

# 2. Install dependencies
uv sync

# 3. Create .env file
cp .env.example .env   # (or create manually)
```

### Required `.env` entries

```env
GEMINI_API_KEY=your_gemini_api_key
GMAIL_CLIENT_ID=your_oauth_client_id
GMAIL_CLIENT_SECRET=your_oauth_client_secret
MANAGER_EMAIL=manager@example.com
```

Google OAuth redirect URI must be added in Cloud Console:
`http://localhost:8000/oauth/callback`

## Usage

```bash
# Web UI (FastAPI) — Dashboard + Google Login + Record Work
python main.py web

# Interactive Chat Agent (Gemini)
python main.py agent

# MCP Server (for external agent integration)
python main.py mcp

# APScheduler — auto daily email (6PM) + month-end payslips
python main.py scheduler
```

## Monthly Excel Format

Each month file (`data/daily_logs/YYYY-MM.xlsx`) contains:

| Sheet | Content |
|-------|---------|
| `_data` (hidden) | Raw flat entries for calculations |
| Per-worker sheet | Merged header + 6 product columns + daily rows + TOTAL |
| `DEPART TOTAL` | Cross-sheet formulas, all workers + GRAND TOTAL |

## Agent Chat Examples

```
You: Kaleem ne 300 nut aur 150 bolt 10*20 kiye
You: Aj ka total kya hai?
You: Sajjad ka payslip banao
You: Manager ko email bhejo
```
