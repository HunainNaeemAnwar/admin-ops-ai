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

for d in [
    DATA_DIR,
    LOG_DIR,
    DAILY_LOGS_DIR,
    PDF_DIR,
    EXCEL_SLIPS_DIR,
    TOKEN_DIR,
    AGENT_MEMORY_DIR,
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
MODEL_FALLBACK_CHAIN_ENV = os.getenv("MODEL_FALLBACK_CHAIN", "")
MODEL_FALLBACK_CHAIN = [
    m.strip() for m in MODEL_FALLBACK_CHAIN_ENV.split(",") if m.strip()
]
if not MODEL_FALLBACK_CHAIN:
    MODEL_FALLBACK_CHAIN = [
        "gpt-oss-120b",  # Primary
        "gpt-oss-120b",  # Fallback 1
        "gpt-oss-120b",  # Fallback 2
    ]

FALLBACK_MODELS = MODEL_FALLBACK_CHAIN


class ModelRouter:
    """Classify user input by complexity and select appropriate model."""

    SIMPLE_KEYWORDS = ["banaye", "production", "product", "absent", "status", "catalog"]
    MEDIUM_KEYWORDS = [
        "summary",
        "report",
        "daily",
        "weekly",
        "monthly",
        "advance",
        "rejection",
    ]
    COMPLEX_KEYWORDS = ["payslip", "salary", "calculate", "email", "send"]

    @classmethod
    def select(cls, user_input: str, fallback_index: int = 0) -> str:
        if fallback_index > 0:
            idx = min(fallback_index, len(MODEL_FALLBACK_CHAIN) - 1)
            return MODEL_FALLBACK_CHAIN[idx]

        text = user_input.lower()
        if any(kw in text for kw in cls.COMPLEX_KEYWORDS):
            return MODEL_FALLBACK_CHAIN[0]
        elif any(kw in text for kw in cls.MEDIUM_KEYWORDS):
            return MODEL_FALLBACK_CHAIN[1]
        else:
            return MODEL_FALLBACK_CHAIN[2]


MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "")
FATHER_EMAIL = os.getenv("FATHER_EMAIL", MANAGER_EMAIL)

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
FIXED_WORKERS = [w.strip() for w in FIXED_WORKERS_ENV.split(",")]

DATABASE_URL = os.getenv("DATABASE_URL", str(DATA_DIR / "admin_ops.db"))

DEFAULT_OPENAI_BASE_URL = "https://api.cerebras.ai/v1"
