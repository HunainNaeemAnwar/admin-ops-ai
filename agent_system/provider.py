import os

from agents.models._openai_shared import set_use_responses_by_default

set_use_responses_by_default(False)

from config import GEMINI_API_KEY, GEMINI_MODEL, DEFAULT_OPENAI_BASE_URL

os.environ["OPENAI_API_KEY"] = GEMINI_API_KEY
os.environ["OPENAI_BASE_URL"] = DEFAULT_OPENAI_BASE_URL
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
