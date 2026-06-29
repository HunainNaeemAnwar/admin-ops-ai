import asyncio
import re
from datetime import date


import config.provider

from openai import RateLimitError, APIStatusError
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner, handoff, ModelSettings, GuardrailFunctionOutput, input_guardrail, InputGuardrailTripwireTriggered, output_guardrail, ToolGuardrailFunctionOutput, tool_output_guardrail
from agents.run_config import RunConfig
from agents.run_error_handlers import RunErrorHandlerResult
from config import FIXED_WORKERS, FALLBACK_MODELS, ROUTER_MODEL
from config.provider import ACTIVE_MODEL, get_model_by_name
from my_agents.utils import load_prompt
from my_agents.specialists.production.agent import create_agent as create_production_agent
from my_agents.specialists.reporting.agent import create_agent as create_reporting_agent
from my_agents.specialists.finance.agent import create_agent as create_finance_agent
from my_agents.memory import ConversationMemory
from my_agents.cost_tracker import track_usage

BASE_RUN_CONFIG = RunConfig(tool_not_found_behavior="return_error_to_model")

_memories: dict[str, ConversationMemory] = {}
_memory_lock = asyncio.Lock()

async def _get_memory(session_id: str = "default") -> ConversationMemory:
    async with _memory_lock:
        if session_id not in _memories:
            _memories[session_id] = ConversationMemory(session_id)
        return _memories[session_id]

async def _remove_memory(session_id: str):
    memory = _memories.pop(session_id, None)
    if memory:
        await memory.delete()
    ConversationMemory.delete_from_db(session_id)

async def _forget_memory(session_id: str):
    """Clear SDK session cache without touching chat_messages table."""
    _memories.pop(session_id, None)
    m = ConversationMemory(session_id)
    await m.delete()

# ── Input Guardrail ────────────────────────────────────

MIN_INPUT_LENGTH = 1
MAX_INPUT_LENGTH = 2000

@input_guardrail(name="Input sanitizer", run_in_parallel=False)
async def _input_sanitizer(
    ctx, agent, input_data: str | list
) -> GuardrailFunctionOutput:
    if isinstance(input_data, str):
        sanitized = input_data.strip()
        if not sanitized:
            return GuardrailFunctionOutput(
                tripwire_triggered=True, output_info="Input is empty."
            )
        if len(sanitized) > MAX_INPUT_LENGTH:
            return GuardrailFunctionOutput(
                tripwire_triggered=True,
                output_info=f"Input too long ({len(sanitized)} chars). Max {MAX_INPUT_LENGTH}.",
            )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info="")

GREETING_PATTERN = re.compile(
    r"^(hel+o+|hi|hey|hye|hie|salam|slm|adaab|khushamdeed|good\s*(morning|evening|afternoon|night|day)|sat\s*sri\s*akal|assalam\s*ualaikum|walekum\s*salam)",
    re.IGNORECASE,
)

@input_guardrail(name="Greeting handler", run_in_parallel=False)
async def _greeting_handler(
    ctx, agent, input_data: str | list
) -> GuardrailFunctionOutput:
    if isinstance(input_data, str):
        text = input_data.strip().rstrip("?!.,;:")
        if GREETING_PATTERN.match(text):
            return GuardrailFunctionOutput(
                tripwire_triggered=True,
                output_info="👋 Hello! Main factory accountant hoon. Production entry, reports, payslips, aur advances handle karta hoon. Aap kya karna chahte hain?",
            )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info="")

# ── Output Guardrails ──────────────────────────────────

FINANCIAL_KEYWORDS = re.compile(
    r"(Rs\s*[\d,]+\.?\d*|salary|wage|payslip|tax|deduction|net\s*payable|gross|rate\s*per\s*piece)",
    re.IGNORECASE,
)

@output_guardrail(name="Financial data protector")
async def _finance_output_guardrail(
    ctx, agent, output: str
) -> GuardrailFunctionOutput:
    """Prevent financial data leakage from non-finance agents."""
    agent_name = getattr(agent, "name", "")
    if agent_name in ("FinanceAgent", "Router"):
        return GuardrailFunctionOutput(tripwire_triggered=False, output_info="")
    if FINANCIAL_KEYWORDS.search(output):
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            output_info="Share the quantity summary without financial breakdown.",
        )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info="")

@tool_output_guardrail
async def _production_tool_output_guardrail(data) -> ToolGuardrailFunctionOutput:
    """Ensure production tool output contains confirmation data."""
    text = str(data.output or "")
    if "Invalid" in text or "error" in text.lower():
        return ToolGuardrailFunctionOutput.reject_content(
            "Entry failed — ask user for corrected data."
        )
    return ToolGuardrailFunctionOutput.allow()

# ── Agent factory ─────────────────────────────────────

WORKER_LIST = ', '.join(FIXED_WORKERS)

def _create_agents(router_model_override=None, specialist_model_override=None):
    s_model = specialist_model_override or router_model_override or ACTIVE_MODEL
    r_model = router_model_override or ACTIVE_MODEL
    today_str = date.today().isoformat()

    prod_settings = ModelSettings(
        temperature=0.2,
        top_p=0.9,
        max_tokens=2000,
        parallel_tool_calls=True,
    )
    report_settings = ModelSettings(
        temperature=0.3,
        top_p=0.9,
        max_tokens=2000,
        parallel_tool_calls=True,
    )
    finance_settings = ModelSettings(
        temperature=0.3,
        top_p=0.9,
        max_tokens=2000,
        parallel_tool_calls=True,
    )

    production_agent = create_production_agent(
        model=s_model,
        model_settings=prod_settings,
        worker_list=WORKER_LIST,
        today_date=today_str,
    )
    reporting_agent = create_reporting_agent(
        model=s_model,
        model_settings=report_settings,
        worker_list=WORKER_LIST,
        today_date=today_str,
        output_guardrails=[_finance_output_guardrail],
    )
    finance_agent = create_finance_agent(
        model=s_model,
        model_settings=finance_settings,
        worker_list=WORKER_LIST,
        today_date=today_str,
    )

    def _router_instructions(ctx, agent) -> str:
        return load_prompt("router.md", {"WORKER_LIST": WORKER_LIST, "TODAY_DATE": date.today().isoformat()})

    router_settings = ModelSettings(
        temperature=0.3,
        top_p=0.9,
        max_tokens=2000,
        parallel_tool_calls=False,
    )
    router = Agent(
        name="Router",
        instructions=_router_instructions,
        model=r_model,
        model_settings=router_settings,
        input_guardrails=[_greeting_handler, _input_sanitizer],
        output_guardrails=[_finance_output_guardrail],
        handoffs=[
            handoff(
                production_agent,
                tool_name_override="delegate_production",
                tool_description_override="Production data entry, tables, absences, and entry edits.",
            ),
            handoff(
                reporting_agent,
                tool_name_override="delegate_reporting",
                tool_description_override="Production summary, daily status, catalog listing, and email reports.",
            ),
            handoff(
                finance_agent,
                tool_name_override="delegate_finance",
                tool_description_override="Payslip generation, advance payments, and rejection recording.",
            ),
        ],
    )
    return router

# ── Chat ──────────────────────────────────────────────

async def chat(user_input: str, session_id: str = "default") -> str:
    memory = await _get_memory(session_id)
    await memory.cleanup()

    existing = await memory.session.get_items()

    if not existing:
        saved = ConversationMemory.load_from_db(session_id)
        if saved:
            await memory.session.add_items(saved)
            existing = saved

    from config.provider import _models as all_models

    fallback_chain = [m for m in FALLBACK_MODELS if m in all_models]
    if not fallback_chain:
        fallback_chain = list(all_models.keys())[:1] or ["mistral"]
    last_error = ""

    for attempt, model_name in enumerate(fallback_chain):
        specialist_model = get_model_by_name(model_name)
        if ROUTER_MODEL and ROUTER_MODEL in all_models:
            router_model = get_model_by_name(ROUTER_MODEL)
        else:
            router_model = specialist_model
        agent = _create_agents(
            router_model_override=router_model,
            specialist_model_override=specialist_model,
        )
        try:
            result = await asyncio.wait_for(
                Runner.run(
                    agent,
                    input=user_input,
                    session=memory.session,
                    max_turns=15,
                    error_handlers={
                        "max_turns": lambda _: RunErrorHandlerResult(
                            final_output="Mujhe is request ko complete karne mein zyada time lag raha hai. Please chhotee request mein tod dein.",
                            include_in_history=False,
                        ),
                    },
                    run_config=BASE_RUN_CONFIG,
                ),
                timeout=30,
            )
            track_usage(session_id, model_name, user_input, str(result.final_output)[:200])
            await memory.compact_if_needed()
            items = await memory.session.get_items()
            ConversationMemory.save_to_db(session_id, items)
            return result.final_output
        except asyncio.TimeoutError:
            return "⚠️ Server busy — please thodi der baad try karein."
        except InputGuardrailTripwireTriggered as e:
            msg = e.guardrail_result.output.output_info or "OK"
            await memory.session.add_items([{"role": "assistant", "content": msg}])
            items = await memory.session.get_items()
            ConversationMemory.save_to_db(session_id, items)
            return msg
        except (RateLimitError, APIStatusError) as e:
            msg = str(e)
            if "Messages with role 'tool'" in msg:
                _memories.pop(session_id, None)
                await memory.delete()
                ConversationMemory.delete_from_db(session_id)
                try:
                    result = await asyncio.wait_for(
                        Runner.run(
                            agent,
                            input=user_input,
                            session=(await _get_memory(session_id)).session,
                            max_turns=15,
                            run_config=BASE_RUN_CONFIG,
                        ),
                        timeout=30,
                    )
                    track_usage(session_id, model_name, user_input, str(result.final_output)[:200])
                    mem = await _get_memory(session_id)
                    await mem.compact_if_needed()
                    items = await mem.session.get_items()
                    ConversationMemory.save_to_db(session_id, items)
                    return result.final_output
                except Exception:
                    return "Memory corrupted — delete kar di. Dobara try karein."
            is_last = attempt == len(fallback_chain) - 1
            prefix = "⚠️ " if is_last else "⚠️ "
            if "429" in msg:
                last_error = f"{prefix}{model_name}: rate limit exceeded"
                continue
            last_error = f"{prefix}{model_name}: {e}"
            continue

    return last_error or "⚠️ Sab models fail ho gaye. Baad mein try karein."

# ── Streaming ─────────────────────────────────────────

async def stream_chat(user_input: str, session_id: str = "default"):
    """Generator that yields SSE-formatted chunks from streaming agent response."""
    memory = await _get_memory(session_id)
    await memory.cleanup()

    existing = await memory.session.get_items()

    if not existing:
        saved = ConversationMemory.load_from_db(session_id)
        if saved:
            await memory.session.add_items(saved)

    from config.provider import _models as all_models

    fallback_chain = [m for m in FALLBACK_MODELS if m in all_models]
    if not fallback_chain:
        fallback_chain = list(all_models.keys())[:1] or ["mistral"]

    for attempt, model_name in enumerate(fallback_chain):
        specialist_model = get_model_by_name(model_name)
        if ROUTER_MODEL and ROUTER_MODEL in all_models:
            router_model = get_model_by_name(ROUTER_MODEL)
        else:
            router_model = specialist_model
        agent = _create_agents(
            router_model_override=router_model,
            specialist_model_override=specialist_model,
        )
        try:
            result = Runner.run_streamed(
                agent,
                input=user_input,
                session=memory.session,
                max_turns=15,
                run_config=BASE_RUN_CONFIG,
            )
            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    if event.data.delta:
                        yield f"data: {event.data.delta}\n\n"

            yield f"data: [DONE]\n\n"
            track_usage(session_id, model_name, user_input, str(result.final_output)[:200])
            await memory.compact_if_needed()
            items = await memory.session.get_items()
            ConversationMemory.save_to_db(session_id, items)
            return
        except InputGuardrailTripwireTriggered as e:
            msg = e.guardrail_result.output.output_info or "OK"
            await memory.session.add_items([{"role": "assistant", "content": msg}])
            items = await memory.session.get_items()
            ConversationMemory.save_to_db(session_id, items)
            yield f"data: {msg}\n\ndata: [DONE]\n\n"
            return
        except (RateLimitError, APIStatusError) as e:
            msg = str(e)
            if "Messages with role 'tool'" in msg:
                _memories.pop(session_id, None)
                await memory.delete()
                ConversationMemory.delete_from_db(session_id)
                yield f"data: Memory corrupted — delete kar di. Dobara try karein.\n\ndata: [DONE]\n\n"
                return
            if attempt == len(fallback_chain) - 1:
                yield f"data: ⚠️ {model_name}: {e}\n\ndata: [DONE]\n\n"
                return
            continue

    yield f"data: ⚠️ Sab models fail ho gaye.\n\ndata: [DONE]\n\n"
