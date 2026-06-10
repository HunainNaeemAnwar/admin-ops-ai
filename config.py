import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DAILY_LOGS_DIR = DATA_DIR / "daily_logs"
PAY_SLIPS_DIR = DATA_DIR / "pay_slips"
PDF_DIR = PAY_SLIPS_DIR / "pdf"
EXCEL_SLIPS_DIR = PAY_SLIPS_DIR / "excel"
PRODUCT_CATALOG_PATH = DATA_DIR / "product_catalog.xlsx"
TOKEN_DIR = DATA_DIR / "tokens"

for d in [DATA_DIR, LOG_DIR, DAILY_LOGS_DIR, PDF_DIR, EXCEL_SLIPS_DIR, TOKEN_DIR]:
    d.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "")

GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
GMAIL_SCOPES = os.getenv(
    "GMAIL_SCOPES",
    "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email",
)
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/oauth/callback")

TAX_PERCENTAGE = float(os.getenv("TAX_PERCENTAGE", "3.0"))

DEFAULT_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
