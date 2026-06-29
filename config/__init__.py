import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = DATA_DIR
LOG_DIR = BASE_DIR / "logs"
DAILY_LOGS_DIR = DATA_DIR / "daily_logs"
PAY_SLIPS_DIR = DATA_DIR / "pay_slips"
PDF_DIR = PAY_SLIPS_DIR / "pdf"
EXCEL_SLIPS_DIR = PAY_SLIPS_DIR / "excel"
PRODUCT_CATALOG_PATH = DATA_DIR / "product_catalog.xlsx"
TOKEN_DIR = DATA_DIR / "tokens"
AGENT_MEMORY_DIR = DATA_DIR / "agent_memory"
HISTORY_DIR = DATA_DIR / "history"

for d in [
    DATA_DIR,
    LOG_DIR,
    DAILY_LOGS_DIR,
    PDF_DIR,
    EXCEL_SLIPS_DIR,
    TOKEN_DIR,
    AGENT_MEMORY_DIR,
    HISTORY_DIR,
]:
    d.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "gpt-oss-120b")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mistral")
FALLBACK_MODELS_ENV = os.getenv("FALLBACK_MODELS", "")
FALLBACK_MODELS = [
    m.strip() for m in FALLBACK_MODELS_ENV.split(",") if m.strip()
]
if not FALLBACK_MODELS:
    all_providers = [LLM_PROVIDER, "gemini", "cerebras", "mistral", "openai"]
    seen = set()
    FALLBACK_MODELS = [
        p for p in all_providers
        if p not in seen and not seen.add(p)
    ]

ROUTER_MODEL = os.getenv("ROUTER_MODEL", "") or None  # Override: different model for Router vs Specialists



MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "")
FATHER_EMAIL = os.getenv("FATHER_EMAIL", MANAGER_EMAIL)
if not FATHER_EMAIL:
    FATHER_EMAIL = None

APP_ENV = os.getenv("APP_ENV", "dev")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FERNET_SECRET = os.getenv("FERNET_SECRET", "")
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
GMAIL_SCOPES = os.getenv(
    "GMAIL_SCOPES",
    "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email",
)
OAUTH_REDIRECT_URI = os.getenv(
    "OAUTH_REDIRECT_URI", "http://localhost:8000/oauth/callback"
)
GMAIL_REDIRECT_URI = os.getenv("GMAIL_REDIRECT_URI", OAUTH_REDIRECT_URI)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

TAX_PERCENTAGE = float(os.getenv("TAX_PERCENTAGE", "3.0"))

RATE_NUT = float(os.getenv("RATE_NUT", "0"))
RATE_10X20 = float(os.getenv("RATE_10X20", "0"))
RATE_6X25 = float(os.getenv("RATE_6X25", "0"))
RATE_6X30 = float(os.getenv("RATE_6X30", "0"))
RATE_10X25 = float(os.getenv("RATE_10X25", "0"))

FIXED_WORKERS_ENV = os.getenv(
    "FIXED_WORKERS", "Naeem,Kaleem,Akbar,Suny,Sajjad,Irfan,Kashif,Gulmast"
)
_raw_workers = [w.strip() for w in FIXED_WORKERS_ENV.split(",") if w.strip()]
if len(_raw_workers) < 2:
    raise ValueError(f"FIXED_WORKERS must have at least 2 workers, got {len(_raw_workers)}: {_raw_workers}")
_non_empty = [w for w in _raw_workers if w]
if len(_non_empty) < len(_raw_workers):
    raise ValueError(f"FIXED_WORKERS contains empty names: {_raw_workers}")
_dupes = set()
for w in _raw_workers:
    if w in _dupes:
        raise ValueError(f"FIXED_WORKERS has duplicate: '{w}'")
    _dupes.add(w)
FIXED_WORKERS = _raw_workers

DATABASE_URL = os.getenv("DATABASE_URL", str(DATA_DIR / "admin_ops.db"))

DEFAULT_OPENAI_BASE_URL = "https://api.cerebras.ai/v1"
