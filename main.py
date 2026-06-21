import sys
import asyncio
from datetime import date, datetime

from dotenv import load_dotenv
load_dotenv()

from config import GEMINI_API_KEY, GMAIL_CLIENT_ID


def check_config():
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        print("ERROR: GEMINI_API_KEY not set in .env file!")
        print("Edit .env and add your Gemini API key.")
        return False
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
                            count = await mem.turn_count()
                            print(f"\n[Memory: {count} items in session '{sid}']")
                        elif cmd == "compact":
                            result = await mem.compact()
                            print(f"\n[Memory: {result}]")
                        elif cmd == "delete":
                            result = await mem.delete()
                            print(f"\n[Memory: {result}]")
                        else:
                            print("\n[Memory: Unknown command. Use: /memory status | compact | delete]")
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
        from fastapi import FastAPI
        from fastapi.staticfiles import StaticFiles
        from fastmcp.utilities.lifespan import combine_lifespans

        from mcp_server import mcp_app as mcp_asgi

        app = FastAPI(title="Admin Ops AI", version="1.0.0", lifespan=combine_lifespans(mcp_asgi.lifespan))
        app.mount("/static", StaticFiles(directory="web_ui/static"), name="static")
        app.mount("/mcp", mcp_asgi)

        from web_ui.routes import router
        app.include_router(router)

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

    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python main.py [mcp|agent|web|scheduler]")


if __name__ == "__main__":
    main()
