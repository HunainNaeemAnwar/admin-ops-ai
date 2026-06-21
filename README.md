# Admin Ops AI v2 — Multi-Agent Accountant System

Factory piece-rate worker tracking system. 8 fixed workers polish 5 different items
(Nut, 10\*20, 6\*25, 6\*30, 10\*25). Daily production recorded per worker per product,
wages auto-calculated with tax deduction, rejection penalty, and advance deduction.
Manager gets daily/weekly/monthly production reports (quantities only, no financials).
Monthly PDF + Excel payslips generated on demand.

**Father (contractor) controls everything via chat interface in Roman Urdu.**
No auto-email, no auto-payslips — father triggers everything.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend (Phase 2) | Next.js + ChatKit |
| Backend | FastAPI + FastMCP |
| Agent SDK | OpenAI Agents SDK 0.17.4 |
| LLM | Gemini 2.5 Flash (OpenAI-compatible endpoint) |
| Database | SQLite (dev) → Neon PostgreSQL (prod) |
| Email | Google OAuth 2.0 + Gmail API |
| Excel Export | openpyxl (templates for reports) |
| PDF Export | reportlab (payslips) |
| Scheduler | APScheduler (reminders only — never auto-execute) |
| Package Manager | UV (Python 3.12+) |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Next.js Frontend (Phase 2)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Chat (ChatKit)│  │ Dashboard    │  │ Auth (Google)     │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────────┘  │
│         │                  │                   │             │
└─────────┼──────────────────┼───────────────────┼─────────────┘
          │           HTTP    │                   │
┌─────────┼──────────────────┼───────────────────┼─────────────┐
│        FastAPI + FastMCP Backend                              │
│  ┌──────┴──────────────────┴───────────────────┴──────────┐  │
│  │              FastAPI Router Layer                      │  │
│  │  /chat  /production  /absent  /rejection  /advance     │  │
│  │  /payslip  /email  /report  /auth  /products           │  │
│  └─────────────────────┬──────────────────────────────────┘  │
│                        │                                    │
│  ┌─────────────────────┴──────────────────────────────────┐  │
│  │           OpenAI Agents SDK (Gemini)                   │  │
│  │  ┌────────────────────────────────────────────────┐   │  │
│  │  │  AccountantOrchestrator Agent                  │   │  │
│  │  │  - 10 function tools (merged for performance)   │   │  │
│  │  │  - Dynamic instructions (callable)               │   │  │
│  │  │  - ConversationMemory (SQLiteSession)            │   │  │
│  │  └────────────────────────────────────────────────┘   │  │
│  └─────────────────────┬──────────────────────────────────┘  │
│                        │                                    │
│  ┌─────────────────────┴──────────────────────────────────┐  │
│  │              Tool Layer                                │  │
│  │  tools/                                                │  │
│  │  ├── database.py      → SQLite/PostgreSQL CRUD         │  │
│  │  ├── production_tools.py → Logging, editing, absent     │  │
│  │  ├── rejection_tools.py  → Rejection recording/distrib  │  │
│  │  ├── advance_tools.py    → Advance payment tracking      │  │
│  │  ├── report_tools.py     → Summaries + manager reports   │  │
│  │  ├── email_tools.py      → Gmail API send (dept only)    │  │
│  │  ├── oauth_tools.py      → Google OAuth PKCE             │  │
│  │  ├── payslip_tools.py    → PDF + Excel payslip export    │  │
│  │  └── export_tools.py     → Excel export for reports      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                        │                                    │
│  ┌─────────────────────┴──────────────────────────────────┐  │
│  │              Database Layer                            │  │
│  │  ┌────────────────────────────────────────────────┐   │  │
│  │  │  SQLite (dev) → Neon PostgreSQL (prod)         │   │  │
│  │  │  Tables: workers, products, daily_log,         │   │  │
│  │  │          rejections, advances, payslips        │   │  │
│  │  │  Excel files: EXPORT ONLY (reports/payslips)   │   │  │
│  │  └────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## Product Codes (Simplified)

| Display Name | Internal Code | Rate Env Var | Since |
|-------------|--------------|--------------|-------|
| NUT | `NUT` | `RATE_NUT` | Always |
| 10\*20 | `10*20` | `RATE_10X20` | Always |
| 6\*25 | `6*25` | `RATE_6X25` | Always |
| 6\*30 | `6*30` | `RATE_6X30` | Always |
| 10\*25 | `10*25` | `RATE_10X25` | 2026+ |

> **No extra product codes.** No NUT-STD, NUT-M10, BOLT-prefixes.
> These 5 simple codes prevent Gemini confusion.
> 10\*25 started production in 2026 — older months have no data for it.

---

## Fixed Workers (8)

| # | Worker | 
|---|--------|
| 1 | Naeem |
| 2 | Kaleem |
| 3 | Akbar |
| 4 | Suny |
| 5 | Sajjad |
| 6 | Irfan |
| 7 | Kashif |
| 8 | Gulmast |

Workers are configurable via `FIXED_WORKERS` env var (comma-separated).

---

## Database Schema (SQLite / PostgreSQL)

### Entity-Relationship

```
workers ──┬──< daily_log >── products
          │
          ├──< advances
          │
          ├──< payslips
          │
rejections (department level, no direct FK to workers)
```

### Tables

```sql
-- ============================================================
-- Workers
-- ============================================================
CREATE TABLE workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- Products (5 items: NUT, 10*20, 6*25, 6*30, 10*25)
-- ============================================================
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,       -- e.g., "NUT", "10*20"
    rate REAL NOT NULL,              -- per-piece rate from env
    tax_pct REAL DEFAULT 3.0,
    active BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- Daily Production Log
-- One row per worker per product per day
-- ============================================================
CREATE TABLE daily_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,               -- "2026-06-16"
    worker_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 0,      -- 0 = worked but didn't make this product
    is_absent BOOLEAN DEFAULT 0,     -- TRUE = worker was on leave
    notes TEXT,                       -- optional (e.g., "half day" if ever needed)
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (worker_id) REFERENCES workers(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    UNIQUE(date, worker_id, product_id)
);

CREATE INDEX idx_daily_log_date ON daily_log(date);
CREATE INDEX idx_daily_log_worker ON daily_log(worker_id);
CREATE INDEX idx_daily_log_product ON daily_log(product_id);

-- ============================================================
-- Monthly Rejections (Department Level)
-- Rejection is recorded per product per month
-- ============================================================
CREATE TABLE rejections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    total_qty INTEGER NOT NULL,           -- e.g., 1000 nuts rejected
    excluded_workers TEXT DEFAULT '[]',   -- JSON array of worker IDs to exempt
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES products(id),
    UNIQUE(year, month, product_id)
);

-- ============================================================
-- Advance Payments
-- ============================================================
CREATE TABLE advances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    date TEXT NOT NULL,                   -- date advance was given
    month INTEGER NOT NULL,               -- which month to deduct in
    year INTEGER NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (worker_id) REFERENCES workers(id)
);

-- ============================================================
-- Payslips (Cached monthly summaries)
-- Generated on father's demand, stored for history
-- ============================================================
CREATE TABLE payslips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    total_gross REAL,
    total_pieces INTEGER,
    rejection_deduction REAL,
    advance_deduction REAL,
    tax_deduction REAL,
    net_payable REAL,
    generated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (worker_id) REFERENCES workers(id),
    UNIQUE(worker_id, year, month)
);
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| One `daily_log` row per worker×product×day | Simple queries, atomic updates, no JSON blobs |
| `is_absent` boolean | Clean absent tracking — no null/magic values |
| `quantity=0` means worked but zero of this product | Distinguishes from `is_absent=TRUE` |
| `rejections` has no FK to workers | Department-level data, workers are excluded via JSON |
| `excluded_workers` is JSON array | Simple, no join table needed |
| `payslips` is cached | Avoids re-calculating every time; regenerate on edit |
| `UNIQUE` constraints everywhere | Prevents duplicate entries from agent errors |

---

## Tools — 10 Merged Tools

Original 16 tools merged into 10 for Gemini 2.5 Flash performance.
Fewer tools = less hallucination, faster response.

| # | Tool | Purpose | Merged From |
|---|------|---------|-------------|
| 1 | `log_production` | Record work — accepts JSON array OR raw text (auto-detects) | `record_work_tool` + `record_work_from_text_tool` |
| 2 | `log_rejection` | Record monthly rejection per product + exclude workers | `record_monthly_rejection_tool` + `exclude_worker_from_rejection_tool` |
| 3 | `record_advance` | Record advance payment to a worker | New |
| 4 | `mark_absent` | Mark worker(s) absent for a specific date | New |
| 5 | `get_daily_status` | Check if today has data + get daily totals | `get_today_work_status_tool` + `get_daily_total_tool` |
| 6 | `get_summary` | Daily / Weekly / Monthly summary with filters | `get_monthly_summary_tool` + weekly logic |
| 7 | `generate_payslip` | Generate PDF + Excel payslip (one worker or all) | `get_worker_payslip_tool` + `generate_all_payslips_tool` |
| 8 | `send_report` | Send daily/weekly/monthly email to manager | `send_email_report_tool` |
| 9 | `update_entry` | Edit an existing production log entry | New |
| 10 | `list_catalog` | List all workers + products in one call | `list_workers_tool` + `list_products_tool` + `get_current_date_tool` |

### Tool Specifications

#### 1. `log_production`

```
Input:
  - data: JSON Array OR natural language string
    JSON: [{"worker": "Kaleem", "products": {"NUT": 300, "10*20": 150}}]
    Text: "Aj sab k 300 nut, 200 6*25 thay aur kaleem nay 6*25 nhi bnaya, kashif ki chutti thi"

Behavior:
  - If text: extract via Gemini structured output
  - If JSON: validate and save directly
  - Auto-detect absent workers from context
  - Always confirm with father before saving
  - Show summary after recording

Returns: Confirmation with per-worker breakdown
```

#### 2. `log_rejection`

```
Input:
  - year, month, product_code, total_qty
  - excluded_workers (optional, array of worker names)

Example:
  log_rejection(year=2026, month=6, product_code="NUT", total_qty=1000)
  → Distribution: 1000/8 = 125 per worker

  log_rejection(year=2026, month=6, product_code="NUT", total_qty=1000, excluded_workers=["Kaleem"])
  → Distribution: 1000/7 ≈ 143 per worker (Kaleem excluded)

Returns: Rejection recorded with distribution breakdown
```

#### 3. `record_advance`

```
Input:
  - worker, amount, month, year
  - description (optional)

Example:
  record_advance(worker="Kaleem", amount=2000, month=6, year=2026)

Returns: Confirmation
```

#### 4. `mark_absent`

```
Input:
  - date (default: today)
  - workers: array of worker names OR "all"

Example:
  mark_absent(date="2026-06-16", workers=["Kashif"])

Returns: Confirmation
```

#### 5. `get_daily_status`

```
Input:
  - date (optional, default: today)

Returns:
  - Has data? Yes/No
  - If yes: per-worker + per-product breakdown, total pieces
  - If no: "NO_DATA — remind father to enter"
```

#### 6. `get_summary`

```
Input:
  - period: "daily" | "weekly" | "monthly"
  - year, month, day (optional)

Returns:
  - Per-product totals (department level)
  - Per-worker breakdown (for father's view)
  - Total pieces, gross, net (financial for father only)
```

#### 7. `generate_payslip`

```
Input:
  - year, month
  - worker (optional: null = ALL workers)

Calculation:
  For each worker:
    gross = Σ(rate × net_qty) per product
    rejection_deduction = Σ(rate × reject_share_qty)
    advance_deduction = Σ(advances for this month)
    tax_deduction = (gross - rejection_deduction) × tax_pct / 100
    net_payable = gross - rejection_deduction - advance_deduction - tax_deduction

Output: PDF + Excel files in data/pay_slips/
Returns: File paths
```

#### 8. `send_report`

```
Input:
  - period: "daily" | "weekly" | "monthly"
  - year, month, day (optional)

Rules (IMMUTABLE):
  - NEVER auto-send — father always triggers
  - NEVER include individual worker data
  - NEVER include financial data (rates, pay, tax, rejection, advance)
  - ONLY department totals per product (quantities)

For weekly/monthly: attach Excel file with production data only
```

#### 9. `update_entry`

```
Input:
  - entry_id (from daily_log)
  - new_quantity
  - reason (optional, for audit)

Example:
  update_entry(entry_id=42, new_quantity=500, reason="Father said original was wrong")

Returns: Old vs new values
```

#### 10. `list_catalog`

```
Input: None

Returns:
  - Workers: [names]
  - Products: [codes with rates, tax_pct]
  - Today's date
```

---

## Agent Architecture

### Single Orchestrator Agent — No Handoffs

One agent, 10 function tools. No sub-agents, no handoffs.

### Dynamic Instructions

```python
def _dynamic_instructions(ctx, agent) -> str:
    return f"""
You are an accounting assistant for a factory.
Fixed workers: {', '.join(FIXED_WORKERS)}.
Today's date: {date.today().isoformat()}

CRITICAL RULES:
1. At conversation start, ALWAYS call get_daily_status FIRST.
2. If NO_DATA: remind father persistently to enter production.
3. NEVER leave a day row empty — every worker=every day has data or "ABSENT".
4. Always ask for confirmation before saving/editing.
5. After recording, show a clear summary.

Products (5): NUT, 10*20, 6*25, 6*30, 10*25
Only these codes exist — reject any other product name.

BEHAVIOR:
- Father speaks Roman Urdu: "Aj sab k 300 nut, 200 6*25"
- "sab k X" → apply X to ALL workers
- "X ne Y nhi bnaya" → set 0 for that product, not absent
- "X ki chutti thi" → mark absent
- Non-existent item → "ye item exist nhi krta"
- Month end (30th/31st): ask "kya payslips bana doon?"
- For rejection: ask which month, which item, what quantity
- Respond in Roman Urdu / English mix

ABSOLUTELY FORBIDDEN:
- Never send email unless father explicitly asks
- Never show financial data in manager emails
- Never leave a day row empty
"""
```

### Memory

- `ConversationMemory` wrapping `SQLiteSession`
- Stored in `data/agent_memory/agent_memory.db`
- CLI commands: `/memory status`, `/memory compact`, `/memory delete`
- Compact keeps system prompt + last 2 exchanges
- Delete clears all

---

## Agent Behavioral Rules

### Production Recording Logic

```
Scenario 1: Father says "Aj sab k 300 nut, 200 6*25 thay"
→ All 8 workers: NUT=300, 6*25=200, other products=0

Scenario 2: Father says "Aj sab k 300 nut, 200 6*25 thay aur kaleem nay 6*25 nhi bnaya"
→ Kaleem: NUT=300, 6*25=0
→ Others: NUT=300, 6*25=200

Scenario 3: Father says "Aj sab k 300 nut, kashif ki chutti thi"
→ All workers: NUT=300
→ Kashif: is_absent=TRUE

Scenario 4: Father says "Kaleem ne 500 nut kiye, Sajjad ne 300 6*30"
→ Kaleem: NUT=500, rest=0
→ Sajjad: 6*30=300, rest=0
→ Others: 0 for all products, NOT absent (just didn't work)

Scenario 5: Father says non-existent item "M10 bolt"
→ Agent: "ye item exist nhi krta. Available hain: NUT, 10*20, 6*25, 6*30, 10*25"
```

### Rejection Handling Logic

```
Father: "June k mahinay main 1000 nut reject hwa"
→ Agent: "June 2026 main 1000 NUT reject record kiye. Default: 8 workers main equally divide?"
→ Father: "Kaleem k rejection mat kato"
→ Agent updates: excluded=["Kaleem"], remaining=7, each share=1000/7≈143

At payslip time:
  For each worker:
    reject_share = total_qty / (total_workers - excluded_count)
    rejection_deduction = reject_share × product_rate
```

---

## Manager Reporting System

### Constitution (Immutable Rules)

```
1. NEVER send email automatically. Father ALWAYS triggers via chat.
2. NEVER include individual worker data in any report.
3. NEVER include financial information — no rates, pay, tax, rejection, advance.
4. ONLY show: department TOTALS per product (quantity in pieces).
```

### Report Formats

| Period | Format | Content |
|--------|--------|---------|
| Daily | Plain text email | Per-product totals across department |
| Weekly | Excel attachment | Day-wise breakdown per product |
| Monthly | Excel attachment | Month totals per product |

### Email Template

```
Subject: Daily Production Summary – 2026-06-16

Dear Manager,

Following is the work completed on 2026-06-16.

Product-wise:
  NUT:      2400 pcs
  10*20:    1600 pcs
  6*25:     800 pcs
  6*30:     0 pcs
  10*25:    0 pcs

Regards,
Admin Ops AI
```

---

## Auth & Access Control

```
User → Google OAuth Login → FastAPI /oauth/callback
  → Check email against FATHER_EMAIL env var
    ├── MATCH → Full access: chat, edit, email, payslips, reports
    └── NO MATCH → Read-only: dashboard, reports (no chat, no edit)
```

### OAuth Flow

```
1. User clicks "Sign in with Google"
2. Redirect to FastAPI /login → Google consent screen
3. Google redirects to FastAPI /oauth/callback
4. FastAPI saves encrypted token, checks FATHER_EMAIL
5. Redirect to FRONTEND_URL (Next.js) with auth status
```

**Two URLs required:**
```env
GMAIL_REDIRECT_URI=http://localhost:8000/oauth/callback
FRONTEND_URL=http://localhost:3000
```

---

## Month Close & Payslip Generation

### No Auto-Trigger

APScheduler exists but is **never used for execution** — only for reminders if configured.

Agent instructions:
> _"Agar date 28-31 hai aur father active hai, toh proactively poch: 'Month end aa raha hai, kya payslips bana doon?'"_

### Payslip Calculation

```
For each worker in {year, month}:

  product_breakdown = []
  for each product:
    total_qty = SUM(daily_log.quantity WHERE worker=X AND product=Y)
    reject_share = get_rejection_share(worker, product, year, month)
    net_qty = total_qty - reject_share
    gross = net_qty × product.rate

  total_gross = Σ gross per product
  rejection_deduction = Σ (reject_share × product.rate)
  advance_deduction = Σ(advances.amount WHERE worker=X AND month=Y)
  taxable = total_gross - rejection_deduction
  tax_deduction = taxable × TAX_PERCENTAGE / 100
  net_payable = total_gross - rejection_deduction - advance_deduction - tax_deduction
```

### Payslip Output

- **PDF**: Via reportlab — table format with product breakdown
- **Excel**: Via openpyxl — structured workbook
- Stored in `data/pay_slips/pdf/` and `data/pay_slips/excel/`
- Father can print PDF for distribution

---

## Edge Cases Register

| # | Edge Case | Handling |
|---|-----------|----------|
| EC1 | Empty day row | **Forbidden** — agent MUST fill data or mark absent |
| EC2 | Sunday with work | Allowed — no fixed holidays, flexible calendar |
| EC3 | Worker started mid-month | Rejection auto-excludes them unless father says otherwise |
| EC4 | Non-existent product mentioned | Agent: _"ye item exist nhi krta. Available: NUT, 10\*20, 6\*25, 6\*30, 10\*25"_ |
| EC5 | Multiple rejections same month | Summed per product, distributed independently |
| EC6 | Rejection after month close | Recorded, father can regenerate payslips |
| EC7 | Edit old entry | `update_entry` tool with old/new audit trail |
| EC8 | Past date entry | Allowed — `date` parameter in `log_production` |
| EC9 | Worker disputes pay | Father checks `get_summary` history → edits if needed |
| EC10 | Email send failure | Agent returns error details with re-auth link |
| EC11 | OAuth token expired | Father told _"re-login karo"_ with login URL |
| EC12 | Future date entry | **Rejected** — cannot log future production |
| EC13 | Non-numeric quantity | Gemini re-prompts (handled by LLM) |
| EC14 | All workers absent | Email: _"No production recorded for this period"_ |
| EC15 | 10\*25 before 2026 | Data column exists but quantity = 0 for old months |
| EC16 | Advance not deducted | If advance date ≠ payslip month, father specifies deduction month |
| EC17 | Rejection with zero workers after exclusion | Error: _"All workers excluded. Rejection not recorded."_ |
| EC18 | Duplicate rejection entry | UNIQUE(year, month, product_id) constraint prevents it |
| EC19 | Worker name typo | Agent warns: _"Kaleem exist krta hai, Kaleem nhi. Correct karun?"_ |
| EC20 | Concurrent edits | SQLite transactions + row-level locking prevent corruption |

---

## Environment Variables

```env
# ── Gemini ──
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# ── Emails ──
MANAGER_EMAIL=manager@company.com
FATHER_EMAIL=hunainnaeemanwar@gmail.com

# ── Google OAuth ──
GMAIL_CLIENT_ID=your_oauth_client_id
GMAIL_CLIENT_SECRET=your_oauth_client_secret
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email openid
GMAIL_REDIRECT_URI=http://localhost:8000/oauth/callback
FRONTEND_URL=http://localhost:3000

# ── Item Rates (per piece in Rs) ──
RATE_NUT=1.0
RATE_10X20=2.0
RATE_6X25=1.5
RATE_6X30=2.5
RATE_10X25=1.75

# ── Tax ──
TAX_PERCENTAGE=3.0

# ── Workers (comma-separated) ──
FIXED_WORKERS=Naeem,Kaleem,Akbar,Suny,Sajjad,Irfan,Kashif,Gulmast

# ── Database ──
DATABASE_URL=sqlite:///data/accounts.db
# Production:
# DATABASE_URL=postgresql://user:pass@host:5432/accounts
```

---

## Project Structure

```
admin-ops-ai/
├── main.py                   # Entry point: agent | web | mcp | scheduler
├── config.py                 # Env vars, paths, constants
├── AGENTS.md                 # Context for AI coding agents
├── README.md                 # This file
├── pyproject.toml            # Dependencies

├── agent_system/
│   ├── __init__.py
│   ├── provider.py           # Gemini via OpenAI-compatible endpoint
│   ├── orchestrator.py       # Agent with 10 tools, memory, chat()
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
│   ├── email_tools.py        # Gmail send (department-only reports)
│   ├── oauth_tools.py        # Google OAuth PKCE, token management
│   ├── payslip_tools.py      # PDF + Excel payslip generation
│   └── export_tools.py       # Excel export for manager reports

├── web_ui/
│   ├── routes.py             # FastAPI routes (Phase 1: REST, Phase 2: Next.js proxy)
│   ├── static/               # Static files
│   └── templates/            # HTML templates (temporary, replaced by Next.js)

├── data/
│   ├── accounts.db           # SQLite database (dev)
│   ├── daily_logs/           # Excel exports (YYYY-MM.xlsx)
│   ├── product_catalog.xlsx  # Product catalog backup
│   ├── agent_memory/         # Conversation memory DB
│   ├── pay_slips/            # Generated payslips
│   │   ├── pdf/
│   │   └── excel/
│   └── tokens/               # Encrypted OAuth tokens

├── scheduler.py              # APScheduler (reminders only)
├── mcp_server.py             # FastMCP server (all 10 tools exposed)
├── template.xlsx             # Excel template for exports
└── seed.py                   # Database seed script (workers + products)
```

---

## Running the System

```bash
# 1. Setup
uv venv
source .venv/bin/activate
uv sync
cp .env.example .env   # Edit with your values

# 2. Seed database (first time only)
python seed.py

# 3. Start
python main.py agent      # CLI Chat Agent (Gemini)
python main.py web        # FastAPI + Dashboard (Phase 1 UI)
python main.py mcp        # FastMCP server (for external agents)
python main.py scheduler  # Reminders only (never auto-executes)
```

## Memory Commands (CLI Agent Mode)

```
/memory status   → Show conversation turn count
/memory compact  → Keep last 2 exchanges, remove older ones
/memory delete   → Full reset, fresh conversation
```

---

## Chat Examples

```text
Father: Aj sab k 300 nut aur 200 6*25 thay
Agent: ✅ Recorded for 8 workers. Summary below:
  Naeem:   NUT=300, 6*25=200
  Kaleem:  NUT=300, 6*25=200
  ...

Father: June k mahinay main 1000 nut reject hwa
Agent: June 2026 main 1000 NUT reject record kiye.
       8 workers equally → 125 per worker. Confirm?

Father: Kaleem k rejection mat kato
Agent: Kaleem excluded. Baqi 7 workers → 143 per worker.

Father: Sab ki payslip banao
Agent: June 2026 ki payslips generate ki:
  Naeem:   data/pay_slips/pdf/Naeem_2026_06.pdf
  Kaleem:  ...

Father: Manager ko daily email bhejo
Agent: Daily summary bhej di manager ko. (quantities only)

Father: Kaleem ko 2000 advance diye
Agent: ✅ Kaleem ke liye Rs 2000 advance record kiye.

Father: Kaleem ka 300 nut galat likha hai, 500 kr do
Agent: Entry #42: 300 → 500. Updated.

Father: Aj k total kitna hua?
Agent: Aaj ka total:
  NUT: 2400 pcs
  10*20: 1600 pcs
  ...
```

---

## Implementation Phases

### Phase 1 — Backend (Current)

```
Step 1: Foundation
  ├── config.py → new env vars
  ├── tools/database.py → SQLite schema, CRUD
  └── seed.py → seed workers + products

Step 2: Core Tools
  ├── tools/production_tools.py  → log_production, mark_absent, update_entry
  ├── tools/rejection_tools.py   → log_rejection, distribution
  ├── tools/advance_tools.py     → record_advance, deduction
  ├── tools/report_tools.py      → get_daily_status, get_summary
  └── tools/export_tools.py      → Excel export

Step 3: Email + Payslip
  ├── tools/email_tools.py    → department-only email
  ├── tools/payslip_tools.py  → PDF + Excel payslips
  └── tools/oauth_tools.py    → update for two-URI flow

Step 4: Agent + API
  ├── agent_system/orchestrator.py → 10 tools, new instructions
  ├── agent_system/data_extractor.py → improved NLP
  ├── mcp_server.py → register 10 tools
  ├── web_ui/routes.py → new endpoints + auth
  └── scheduler.py → disable auto, keep reminders

Step 5: Migrate old Excel data to SQLite
  └── migration script
```

### Phase 2 — Frontend (Next.js + ChatKit)

```
TBD — planned after Phase 1 completion
```
