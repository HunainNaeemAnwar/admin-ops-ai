# Data Model: Agent Core Optimizations

This feature introduces NO new database tables. All changes are in-memory/logical entities that extend the existing SQLite-based persistence layer.

## Logical Entities

### ModelRouter

| Field | Type | Description |
|-------|------|-------------|
| SIMPLE_KEYWORDS | `list[str]` | Keywords that trigger lightweight model: banaye, production, product, absent, status, catalog |
| MEDIUM_KEYWORDS | `list[str]` | Keywords that trigger mid-tier model: summary, report, daily, weekly, monthly, advance, rejection |
| COMPLEX_KEYWORDS | `list[str]` | Keywords that trigger primary model: payslip, salary, calculate, email, send |
| selected_model | `str` | Model ID chosen after keyword matching + fallback logic |

**Behavior:**
- Classification is stateless — computed fresh per user input
- If no keywords match, defaults to lightweight model
- Fallback index increments on rate-limit errors

### BatchUpdate

| Field | Type | Description |
|-------|------|-------------|
| entries_json | `str` | JSON array of production entries `[{"worker", "product_code", "quantity"}]` |
| absent_workers | `Optional[str]` | JSON array of worker names to mark absent `["Naeem", "Sajjad"]` or null |

**Behavior:**
- Composite operation — production logging + absent marking in one tool call
- Partial success: valid entries saved, invalid entries reported with specific errors
- Uses existing `log_production_json()` and `prod_mark_absent()` internally

### ConversationMemory (extended)

| Field | Type | Description |
|-------|------|-------------|
| MAX_TOKENS_ESTIMATE | `int` | Threshold for auto-compaction (8000) |
| _session | `SQLiteSession` | Underlying SDK session storage |
| session_id | `str` | Unique session identifier |

**New method:**
- `compact_if_needed()` — checks token estimate against threshold, auto-compacts if exceeded
- `_estimate_tokens(items)` — rough token count via `len(str(item)) // 4`

### DatabaseConnection

| Field | Type | Description |
|-------|------|-------------|
| _local | `threading.local()` | Thread-local storage for connection |
| conn | `sqlite3.Connection \| None` | Cached connection per thread |

**Behavior:**
- First call per thread creates connection with WAL + foreign keys
- Subsequent calls on same thread reuse existing connection
- No explicit close needed — connection lives for thread lifetime
- Compatible with existing all CRUD functions (they call `get_db()`)

## State Transitions

None. No new state machines introduced. All changes are transparent optimizations of existing data flows.

## Relationship to Existing Schema

| Existing Table | Impact |
|---------------|--------|
| workers | No change. Batch tool reads via existing `get_worker_id()` |
| products | No change. Batch tool reads via existing `get_product_info()` |
| daily_log | No change. Batch tool writes via existing `log_production()` |
| rejections | No change. Not affected. |
| advances | No change. Not affected. |
| payslips | No change. Not affected. |
