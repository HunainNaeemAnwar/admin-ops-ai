# Contracts: Agent Core Optimizations

## ModelRouter

### `ModelRouter.select(user_input, fallback_index=0) → str`

Classifies user input and returns the appropriate model ID.

**Input:**
- `user_input`: Raw user text (e.g., "aj ka status do", "June ki payslip banao")
- `fallback_index`: 0 for first attempt, >0 for consecutive rate-limit retries

**Output:**
- Model ID string from `MODEL_FALLBACK_CHAIN`:
  - Simple query → `gemini-2.5-flash-lite`
  - Medium query → `gemini-1.5-flash`
  - Complex query → `gemini-2.5-flash`

**Side Effects:** None. Stateless classification.

**Error Handling:** If no model is available (all rate-limited), `chat()` returns error message to user.

---

## Batch Daily Update Tool

### `batch_daily_update_tool(entries_json, absent_workers) → str`

Composite operation: record production entries AND mark absent workers in a single tool call.

**Input:**
- `entries_json` (str, required): JSON array. Format:
  ```json
  [{"worker": "Kaleem", "product_code": "NUT", "quantity": 300}]
  ```
- `absent_workers` (str | None, optional): JSON array of worker names.
  ```json
  ["Naeem", "Sajjad"]
  ```

**Output:**
- Formatted string with results per operation:
  ```
  [Production]
    Kaleem: 300xNUT
    Naeem: 200x10*20

  [Absent]
  Marked Sajjad absent for 2026-06-22
  ```

**Error Handling:**
- Invalid JSON → `"[Production] Invalid JSON: ..."` — doesn't crash, continues
- Invalid worker name → reports error per entry, valid ones still saved
- Duplicate entry → updates quantity and reports "updated"

---

## ConversationMemory

### `compact_if_needed() → str`

Checks token estimate and auto-compacts if threshold exceeded.

**Input:** None (uses internal session state)

**Output:**
- If under threshold: `"Memory OK (~{tokens} tokens)"`
- If over threshold: `"Memory compacted: {before}→{after} items (~{tokens} tokens)"`

**Behavior:**
- Retains system prompt (first item) + last 6 exchanges
- Uses `len(str(item)) // 4` for token estimation
- Called automatically at end of every `chat()` turn

---

## Database Connection

### `get_db() → sqlite3.Connection`

Returns a thread-local cached SQLite connection.

**Input:** None

**Output:** `sqlite3.Connection` with:
- `row_factory = sqlite3.Row`
- `PRAGMA journal_mode=WAL`
- `PRAGMA foreign_keys=ON`

**Behavior:**
- Thread-local storage: each thread gets its own connection on first call
- Subsequent calls on same thread return cached connection
- No explicit close needed (closed on thread exit)

**Edge Cases:**
- If thread dies, connection is garbage collected
- WAL checkpoint handled automatically by SQLite
- Multiple threads each have independent connections — no locking issues
