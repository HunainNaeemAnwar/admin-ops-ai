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
        print("Usage: python main.py [mcp|agent|web|scheduler]")
        print("  mcp       - FastMCP server (for external agents)")
        print("  agent     - Interactive OpenAI Agents SDK chat")
        print("  web       - FastAPI web UI (with Google OAuth login)")
        print("  scheduler - APScheduler auto daily/monthly jobs")
        sys.exit(1)

    mode = sys.argv[1]
    print_banner(mode)

    if mode == "mcp":
        from mcp_server import mcp
        mcp.run()

    elif mode == "agent":
        from agent_system.orchestrator import chat
        print("Accountant Agent ready! Type 'exit' to quit.")
        print("Examples:")
        print('  - "Aj ka total kya hai?"')
        print('  - "Ahmed ne 50 bolt 10*20 aur 30 nuts kiye"')
        print('  - "Ali ka payslip banao"')
        print('  - "Manager ko email bhejo"')
        print()

        async def interactive():
            while True:
                try:
                    user_input = input("\nYou: ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ("exit", "quit", "bye"):
                        print("Accountant Agent: Khuda Hafiz!")
                        break
                    print("\nAccountant Agent: Thinking...")
                    response = await chat(user_input)
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

        app = FastAPI(title="Admin Ops AI", version="1.0.0")
        app.mount("/static", StaticFiles(directory="web_ui/static"), name="static")

        from web_ui.routes import router
        app.include_router(router)

        if not GMAIL_CLIENT_ID or GMAIL_CLIENT_ID == "your_client_id":
            print("\n⚠️  GMAIL_CLIENT_ID not configured!")
            print("   Google OAuth login will not work until you set it in .env")
            print()

        print("Web UI: http://localhost:8000")
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
