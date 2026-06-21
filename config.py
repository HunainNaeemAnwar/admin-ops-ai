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

for d in [DATA_DIR, LOG_DIR, DAILY_LOGS_DIR, PDF_DIR, EXCEL_SLIPS_DIR, TOKEN_DIR, AGENT_MEMORY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODELS_ENV = os.getenv("FALLBACK_MODELS", "")
FALLBACK_MODELS = [m.strip() for m in FALLBACK_MODELS_ENV.split(",") if m.strip()]
if not FALLBACK_MODELS:
    FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash", "gemini-3.1-flash", "gemini-3.1-flash-lite"]

MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "")
FATHER_EMAIL = os.getenv("FATHER_EMAIL", MANAGER_EMAIL)

GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
GMAIL_SCOPES = os.getenv(
    "GMAIL_SCOPES",
    "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email",
)
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/oauth/callback")
GMAIL_REDIRECT_URI = os.getenv("GMAIL_REDIRECT_URI", OAUTH_REDIRECT_URI)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

TAX_PERCENTAGE = float(os.getenv("TAX_PERCENTAGE", "3.0"))

RATE_NUT = float(os.getenv("RATE_NUT", "0"))
RATE_10X20 = float(os.getenv("RATE_10X20", "0"))
RATE_6X25 = float(os.getenv("RATE_6X25", "0"))
RATE_6X30 = float(os.getenv("RATE_6X30", "0"))
RATE_10X25 = float(os.getenv("RATE_10X25", "0"))

FIXED_WORKERS_ENV = os.getenv("FIXED_WORKERS", "Naeem,Kaleem,Akbar,Suny,Sajjad,Irfan,Kashif,Gulmast")
FIXED_WORKERS = [w.strip() for w in FIXED_WORKERS_ENV.split(",")]

DATABASE_URL = os.getenv("DATABASE_URL", str(DATA_DIR / "admin_ops.db"))

DEFAULT_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
