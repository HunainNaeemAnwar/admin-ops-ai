# Quickstart: Agent Core Optimizations

## What Changed

This feature optimizes the agent's core execution path. No new user-facing features added. All changes are under-the-hood performance improvements.

## For Users

- **Multi-instruction messages are faster**: Send "Kaleem ne 300 NUT aur 150 10*20 kiye, Sajjad ko absent karo" — all process in 1-2 turns.
- **Simple queries use cheaper models**: Status checks and catalog lookups route to a faster, cheaper model automatically.
- **Memory auto-manages**: Long conversations stay fast without manual `/memory compact`.
- **Everything works the same**: Production recording, rejection, advance, payslip, email — no changes.

## For Developers

### Key Files Modified

| File | Change |
|------|--------|
| `config.py` | Added `ModelRouter` class with keyword-based complexity classification |
| `tools/database.py` | Thread-local `get_db()` cache using `threading.local()` |
| `agent_system/orchestrator.py` | `run_llm_again` + `parallel_tool_calls=True`, `batch_daily_update_tool`, `ModelRouter` integration in `chat()`, `ProductionEntry` Pydantic model, dynamic instructions updated |
| `agent_system/memory_manager.py` | Token-based `compact_if_needed()` with `MAX_TOKENS_ESTIMATE=8000` |
| `main.py` | `/memory status` now shows estimated token count |

### Testing

```bash
# Syntax check
uv run python -c "import py_compile; py_compile.compile('config.py', doraise=True); py_compile.compile('tools/database.py', doraise=True); py_compile.compile('agent_system/orchestrator.py', doraise=True)"

# Manual: multi-instruction test (US1)
uv run python main.py agent
# → Input: "Kaleem ne 300 NUT aur 150 10*20 kiye, Sajjad ko absent karo, aur aaj ka status do"
# → Expected: Tools execute in parallel, human-readable confirmation, ≤2 turns

# Manual: model routing test (US2)
# → Input: "aj ka status kya hai"
# → Expected: Uses lightweight model (gemini-2.5-flash-lite)
# → Input: "June 2026 ki payslip banao"
# → Expected: Uses primary model (gemini-2.5-flash)

# Manual: batch tool test (US3)
# → Input: "Kaleem ne 300 NUT, Naeem 200 10*20, Sajjad ko absent karo"
# → Expected: Single batch tool call processes all operations

# Manual: auto-compaction test (US4)
# → Run 10+ turns, then /memory status
# → Expected: Token count shown, auto-compaction keeps responses fast

# Manual: regression test
# → Test existing flows: production, rejection, advance, payslip, email
# → Expected: All existing functionality works without changes
```
