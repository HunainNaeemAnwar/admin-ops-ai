# Feature Specification: Agent Core Optimizations

**Feature Branch**: `002-agent-core-optimizations`
**Created**: 2026-06-22
**Status**: Draft
**Input**: User description: "Agent core optimizations: switch to run_llm_again, enable parallel tool calls, add composite batch tool, add Pydantic structured inputs, add ModelRouter for complexity-based model selection, improve context window management with token-based auto-compaction, add thread-local database connection cache"

## User Scenarios & Testing

### User Story 1 - Father sends multi-instruction message, agent executes efficiently (Priority: P1)

The father sends a single message containing multiple instructions (e.g., "record production for Kaleem and Naeem, mark Sajjad absent, then show today's status"). The agent processes all instructions in minimal turns, executing independent tool calls in parallel within a single turn.

**Why this priority**: This is the most frequent interaction pattern. The father routinely sends multi-worker, multi-action messages. Optimizing this flow directly reduces response time and improves daily workflow efficiency.

**Independent Test**: Can be fully tested by sending a message with 3 instructions (e.g., production + absent + status) and verifying all execute in 1-2 LLM turns instead of 3-4 turns.

**Acceptance Scenarios**:

1. **Given** the agent is running with parallel tool calls enabled, **When** the father sends "Kaleem ne 300 NUT aur 150 10*20 kiye, Sajjad ko absent karo, aur aaj ka status do", **Then** the agent executes production logging, absent marking, and status retrieval with at most 2 LLM turns (tools in parallel, then LLM processes results).
2. **Given** multiple tool calls are dispatched in parallel, **When** one tool fails (e.g., duplicate entry), **Then** the remaining tools still complete successfully and the error is reported for the failed one only.
3. **Given** the agent switches from `stop_on_first_tool` to `run_llm_again`, **When** a tool returns results, **Then** the LLM processes the results and generates a natural language confirmation rather than raw tool output.

---

### User Story 2 - Father sends a simple query, lightweight model handles it (Priority: P2)

The father asks a simple question like "aj kitne log aaye?" or "Naeem ka status kya hai?". The ModelRouter detects this as a low-complexity query and routes it to a faster, cheaper model (gemini-2.5-flash-lite) instead of the primary model.

**Why this priority**: Significant cost savings and speed improvement for the most common query type. Simple status checks and catalog lookups form ~60% of daily interactions and don't need the full model.

**Independent Test**: Can be tested by sending a simple status query and verifying via trace/logs that a lighter model was selected.

**Acceptance Scenarios**:

1. **Given** the father sends a simple query like "aj ka status kya hai", **When** ModelRouter classifies it as simple, **Then** the agent runs on a lightweight model and returns results within 2 seconds.
2. **Given** the father sends a complex query like "June 2026 ki payslip banao", **When** ModelRouter classifies it as complex, **Then** the agent runs on the primary model.
3. **Given** the selected model hits a rate limit, **When** fallback chain activates, **Then** the next model in chain is tried automatically.

---

### User Story 3 - Father uses batch daily update for all morning entries (Priority: P2)

The father sends a combined production + absent update in a single structured message. The batch tool handles both production logging and absent marking in one composite operation.

**Why this priority**: Reduces LLM turn count for the daily morning routine (recording yesterday's production and marking absent workers). From 3-4 separate tool calls to 1 composite call.

**Independent Test**: Can be tested by calling the batch tool with production entries + absent workers list and verifying all records are saved correctly.

**Acceptance Scenarios**:

1. **Given** the father sends "Kaleem ne 300 NUT, Naeem 200 10*20, Sajjad ko absent karo", **When** the batch tool is called, **Then** production entries are saved and absent marking is completed in a single tool execution.
2. **Given** invalid JSON is passed to the batch tool, **When** parsing fails, **Then** a clear error message is returned without crashing or losing valid entries.
3. **Given** the batch tool processes 10+ entries, **When** all operations succeed, **Then** a consolidated confirmation shows results for each operation.

---

### User Story 4 - Long conversation sessions maintain fast response times (Priority: P3)

The father has been chatting with the agent for 50+ turns across multiple days. The conversation history is automatically compacted to keep token usage within limits, preventing slowdown and excessive costs.

**Why this priority**: Important for production usage but doesn't block daily workflows. Memory management becomes critical after 2+ weeks of daily use.

**Independent Test**: Can be tested by running 20+ conversation turns, then checking that auto-compaction triggers and keeps response times consistent.

**Acceptance Scenarios**:

1. **Given** a conversation has grown beyond the token threshold, **When** the next turn completes, **Then** memory is auto-compacted, keeping the most recent 6 exchanges plus system prompt.
2. **Given** memory compaction has occurred, **When** the father continues the conversation, **Then** the agent still has sufficient context from recent history to respond accurately.
3. **Given** the father explicitly runs `/memory status`, **When** the command executes, **Then** the current estimated token count is shown.

---

### Edge Cases

- What happens when all models in the ModelRouter chain are rate-limited? The system returns a clear "All models currently rate-limited, try again" message.
- How does the system handle a batch tool call where some entries are valid and some are invalid? Valid entries are saved, invalid ones are reported with specific errors, remaining operations continue.
- What happens when parallel tool calls conflict (e.g., marking a worker absent who already has production entries)? The conflicting tool returns an error, other parallel calls continue unaffected.
- How does auto-compaction handle a session with only 2-3 exchanges? It detects token count is below threshold and does nothing.

## Requirements

### Functional Requirements

- **FR-001**: The agent MUST execute tool calls with `run_llm_again` behavior — tool results are sent back to the LLM for processing rather than stopping at the first tool output.
- **FR-002**: The agent MUST support parallel tool calls — when the LLM emits multiple independent tool calls in a single turn, they MUST execute concurrently within a single LLM round-trip.
- **FR-003**: A composite batch tool MUST be available that accepts production entries AND absent worker lists in a single call and processes both atomically.
- **FR-004**: The batch tool MUST validate JSON input and return clear error messages for invalid entries while continuing to process valid ones.
- **FR-005**: A ModelRouter MUST classify user input by complexity and select the appropriate model — lightweight model for simple queries, primary model for complex operations.
- **FR-006**: The ModelRouter MUST fall back through the model chain if the selected model is rate-limited.
- **FR-007**: Conversation memory MUST auto-compact when estimated token count exceeds a configurable threshold, preserving the system prompt and most recent exchanges.
- **FR-008**: The database connection layer MUST reuse connections within the same thread to eliminate open/close overhead for consecutive tool calls.
- **FR-009**: The dynamic instructions MUST be updated to reflect `run_llm_again` behavior — the agent should generate human-readable results after tool execution, not raw tool output.
- **FR-010**: Tool inputs that accept raw JSON strings SHOULD use Pydantic models for schema generation in tool descriptions to improve LLM accuracy.

### Key Entities

- **ModelRouter**: Classification engine that maps user input keywords to model tiers (simple/medium/complex) and selects the appropriate model from the fallback chain.
- **BatchUpdate**: Composite operation envelope that contains both production entries and absent-worker lists for single-call processing.
- **ConversationMemory**: Token-aware session manager that monitors conversation size and triggers auto-compaction when thresholds are exceeded.
- **DatabaseConnection**: Thread-local connection provider that caches the SQLite connection per thread, eliminating repeated open/close overhead.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Multi-instruction messages (3+ instructions) complete in at most 2 LLM turn cycles, down from 3-4 turn cycles.
- **SC-002**: Simple queries (status checks, catalog lookups) are answered within 2 seconds end-to-end using the lightweight model.
- **SC-003**: Batch daily update operations reduce LLM turn count by at least 50% for combined production + absent workflows.
- **SC-004**: Conversation sessions with 50+ turns maintain consistent response time with no degradation from accumulated history.
- **SC-005**: Database connection overhead per tool call chain is reduced to near-zero through thread-local connection reuse.
- **SC-006**: No functional regressions — all existing production recording, rejection, advance, payslip, and email tools continue to work correctly after changes.
