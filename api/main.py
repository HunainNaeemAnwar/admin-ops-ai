import sys
from datetime import date

from dotenv import load_dotenv
load_dotenv()

from config import (
    OPENAI_API_KEY, GMAIL_CLIENT_ID,
    LLM_PROVIDER, CEREBRAS_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY,
)


def check_config():
    provider_key_map = {
        "cerebras": ("CEREBRAS_API_KEY", CEREBRAS_API_KEY),
        "gemini": ("GEMINI_API_KEY", GEMINI_API_KEY),
        "mistral": ("MISTRAL_API_KEY", MISTRAL_API_KEY),
        "openai": ("OPENAI_API_KEY", OPENAI_API_KEY),
    }
    if LLM_PROVIDER in provider_key_map:
        key_name, key_value = provider_key_map[LLM_PROVIDER]
        if not key_value:
            print(f"ERROR: {key_name} not set in .env file!")
            print(f"LLM_PROVIDER is '{LLM_PROVIDER}' but corresponding API key is missing.")
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
        print("Usage: python -m api.main [web|seed]")
        print("  web       - FastAPI web UI (with Google OAuth login)")
        print("  seed      - Seed database with workers and products")
        sys.exit(1)

    mode = sys.argv[1]
    print_banner(mode)

    if mode == "seed":
        from services.database import init_memory_db
        init_memory_db()
        from config.seed import seed
        seed()
        print("Database seeded successfully.")

    elif mode == "web":
        import uvicorn
        from contextlib import asynccontextmanager
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.staticfiles import StaticFiles
        from api.middleware.middleware import (
            RateLimitMiddleware, RateLimiter,
            CorrelationIDMiddleware,
            register_shutdown_hook, setup_signal_handlers,
        )

        @asynccontextmanager
        async def _warmup_lifespan(app):
            from services.database import init_db, init_memory_db
            init_db()
            init_memory_db()
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

        app = FastAPI(title="Admin Ops AI", version="1.0.0", lifespan=_warmup_lifespan)
        app.add_middleware(CorrelationIDMiddleware)
        app.add_middleware(RateLimitMiddleware, rate_limiter=RateLimiter(max_requests=120, window_seconds=60))
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-Auth-Token"],
        )
        app.mount("/static", StaticFiles(directory="api/static"), name="static")

        from api.routes import router, admin_router
        app.include_router(router)
        app.include_router(admin_router)

        from api.middleware.middleware import (
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
            print("\nERROR: GMAIL_CLIENT_ID not configured!")
            print("   Google OAuth login will not work until you set it in .env")
            print("   Exiting.")
            sys.exit(1)

        print("Web UI: http://localhost:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000)

    elif mode == "backfill":
        print("Backfilling history from daily_log...")
        from services.database import backfill_history
        result = backfill_history()
        print(result["message"])
        if result["months"]:
            for m in result["months"]:
                print(f"  Archived: {m['year']}-{m['month']:02d}")

    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python -m api.main [web|seed|backfill]")


if __name__ == "__main__":
    main()
