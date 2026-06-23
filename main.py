import sys
import asyncio
from datetime import date, datetime

from dotenv import load_dotenv
load_dotenv()

from config import CEREBRAS_API_KEY, OPENAI_API_KEY, GMAIL_CLIENT_ID


def check_config():
    if not CEREBRAS_API_KEY or CEREBRAS_API_KEY == "your_cerebras_api_key_here":
        print("ERROR: CEREBRAS_API_KEY not set in .env file!")
        print("Edit .env and add your Cerebras API key.")
        return False
    if not OPENAI_API_KEY:
        print("WARNING: OPENAI_API_KEY not set — tracing will not be exported to OpenAI dashboard.")
        print("Set OPENAI_API_KEY in .env to view traces at https://platform.openai.com/traces.")
    return True


def print_banner(mode: str):
    sep = "=" * 60
    print(sep)
    print(f"  Admin Ops AI - Accountant Multi-Agent System")
    print(f"  Mode: {mode}")
    print(f"  Date: {date.today().isoformat()}")
    print(sep)
    print()


def main():
    if not check_config():
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python main.py [mcp|agent|web|scheduler|seed]")
        print("  mcp       - FastMCP server (for external agents)")
        print("  agent     - Interactive OpenAI Agents SDK chat")
        print("  web       - FastAPI web UI (with Google OAuth login)")
        print("  scheduler - APScheduler (reminder-only mode)")
        print("  seed      - Seed database with workers and products")
        sys.exit(1)

    mode = sys.argv[1]
    print_banner(mode)

    if mode == "seed":
        from seed import seed
        seed()
        print("Database seeded successfully.")

    elif mode == "mcp":
        from mcp_server import mcp
        mcp.run()

    elif mode == "agent":
        from agent_system.orchestrator import chat, _get_memory
        _agent_session_id = "default"
        print("Accountant Agent ready! Type 'exit' to quit.")
        print("Memory commands:")
        print('  /memory status   - Check memory size')
        print('  /memory compact  - Compact memory (keep last 2 exchanges)')
        print('  /memory cleanup  - Remove corrupted/tool messages')
        print('  /memory delete   - Delete all memory (fresh start)')
        print()
        print("Examples:")
        print('  - "Aj ka total kya hai?"')
        print('  - "Kaleem ne 300 nut aur 150 10*20 kiye"')
        print('  - "Sab ki payslip banao June 2026"')
        print('  - "Manager ko daily email bhejo"')
        print()

        async def interactive():
            sid = _agent_session_id
            while True:
                try:
                    user_input = input("\nYou: ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ("exit", "quit", "bye"):
                        print("Accountant Agent: Khuda Hafiz!")
                        break

                    if user_input.startswith("/memory"):
                        parts = user_input.split()
                        cmd = parts[1] if len(parts) > 1 else ""
                        mem = _get_memory(sid)
                        if cmd == "status":
                            items = await mem._session.get_items()
                            count = len(items)
                            tokens = sum(len(str(i)) for i in items) // 4
                            print(f"\n[Memory: {count} items, ~{tokens} tokens in session '{sid}']")
                        elif cmd == "compact":
                            result = await mem.compact()
                            print(f"\n[Memory: {result}]")
                        elif cmd == "delete":
                            result = await mem.delete()
                            print(f"\n[Memory: {result}]")
                        elif cmd == "cleanup":
                            result = await mem.cleanup()
                            print(f"\n[Memory: {result}]")
                        elif cmd == "cost":
                            from agent_system.cost_tracker import format_session_cost
                            print(f"\n{format_session_cost(sid)}")
                        else:
                            print("\n[Memory: Unknown command. Use: /memory status | compact | delete | cleanup | cost]")
                        continue

                    print("\nAccountant Agent: Thinking...")
                    response = await chat(user_input, sid)
                    print(f"\nAccountant Agent: {response}")
                except KeyboardInterrupt:
                    print("\n\nBye!")
                    break
                except Exception as e:
                    print(f"\nError: {e}")

        asyncio.run(interactive())

    elif mode == "web":
        import uvicorn
        from contextlib import asynccontextmanager
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.staticfiles import StaticFiles
        from fastmcp.utilities.lifespan import combine_lifespans

        from mcp_server import mcp_app as mcp_asgi
        from web_ui.middleware import (
            RateLimitMiddleware, RateLimiter,
            CorrelationIDMiddleware,
            register_shutdown_hook, setup_signal_handlers,
        )

        @asynccontextmanager
        async def _warmup_lifespan(app):
            try:
                from openai import AsyncOpenAI
                from config import CEREBRAS_API_KEY, DEFAULT_OPENAI_BASE_URL, CEREBRAS_MODEL
                client = AsyncOpenAI(api_key=CEREBRAS_API_KEY, base_url=DEFAULT_OPENAI_BASE_URL)
                await client.chat.completions.create(
                    model=CEREBRAS_MODEL,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=1,
                )
                print("[Warmup] Cerebras API connection ready")
            except Exception as e:
                print(f"[Warmup] Cerebras API not reachable: {e}")
            yield

        merged_lifespan = combine_lifespans(mcp_asgi.lifespan, _warmup_lifespan)
        app = FastAPI(title="Admin Ops AI", version="1.0.0", lifespan=merged_lifespan)
        app.add_middleware(CorrelationIDMiddleware)
        app.add_middleware(RateLimitMiddleware, rate_limiter=RateLimiter(max_requests=120, window_seconds=60))
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )
        app.mount("/static", StaticFiles(directory="web_ui/static"), name="static")
        app.mount("/mcp", mcp_asgi)

        from web_ui.routes import router, admin_router
        app.include_router(router)
        app.include_router(admin_router)

        from web_ui.middleware import (
            global_validation_error_handler, global_http_error_handler,
            global_unhandled_error_handler, MaxBodySizeMiddleware,
        )
        from fastapi.exceptions import RequestValidationError, HTTPException as FastAPIHTTPException
        from starlette.exceptions import HTTPException as StarletteHTTPException
        app.add_middleware(MaxBodySizeMiddleware, max_body_size=1_048_576)
        app.add_exception_handler(RequestValidationError, global_validation_error_handler)
        app.add_exception_handler(FastAPIHTTPException, global_http_error_handler)
        app.add_exception_handler(StarletteHTTPException, global_http_error_handler)
        app.add_exception_handler(Exception, global_unhandled_error_handler)

        register_shutdown_hook(lambda: print("[Shutdown] DB connections closed."))
        setup_signal_handlers()

        if not GMAIL_CLIENT_ID or GMAIL_CLIENT_ID == "your_client_id":
            print("\n⚠️  GMAIL_CLIENT_ID not configured!")
            print("   Google OAuth login will not work until you set it in .env")
            print()

        print("Web UI: http://localhost:8000")
        print("MCP Server: http://localhost:8000/mcp")
        uvicorn.run(app, host="0.0.0.0", port=8000)

    elif mode == "scheduler":
        from scheduler import setup_scheduler
        setup_scheduler()
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            print("\nScheduler stopped.")

    elif mode == "backfill":
        print("Backfilling history from daily_log...")
        from tools.database import backfill_history
        result = backfill_history()
        print(result["message"])
        if result["months"]:
            for m in result["months"]:
                print(f"  Archived: {m['year']}-{m['month']:02d}")

    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python main.py [mcp|agent|web|scheduler|backfill]")


if __name__ == "__main__":
    main()
