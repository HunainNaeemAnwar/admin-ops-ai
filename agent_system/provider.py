import os

from agents.models._openai_shared import set_use_responses_by_default

set_use_responses_by_default(False)

from config import (
    OPENAI_API_KEY,
    CEREBRAS_API_KEY,
    CEREBRAS_MODEL,
    DEFAULT_OPENAI_BASE_URL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MISTRAL_API_KEY,
    MISTRAL_MODEL,
    MISTRAL_BASE_URL,
    LLM_PROVIDER,
)

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

_models: dict[str, OpenAIChatCompletionsModel] = {}

if MISTRAL_API_KEY:
    _models["mistral"] = OpenAIChatCompletionsModel(
        model=MISTRAL_MODEL,
        openai_client=AsyncOpenAI(api_key=MISTRAL_API_KEY, base_url=MISTRAL_BASE_URL),
    )

if GEMINI_API_KEY:
    _models["gemini"] = OpenAIChatCompletionsModel(
        model=GEMINI_MODEL,
        openai_client=AsyncOpenAI(api_key=GEMINI_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/"),
    )

if CEREBRAS_API_KEY:
    _models["cerebras"] = OpenAIChatCompletionsModel(
        model=CEREBRAS_MODEL,
        openai_client=AsyncOpenAI(api_key=CEREBRAS_API_KEY, base_url=DEFAULT_OPENAI_BASE_URL),
    )

if OPENAI_API_KEY:
    _models["openai"] = OpenAIChatCompletionsModel(
        model="gpt-4o-mini",
        openai_client=AsyncOpenAI(api_key=OPENAI_API_KEY),
    )

ACTIVE_MODEL = _models.get(LLM_PROVIDER) or next(iter(_models.values()))


def get_model_by_name(name: str) -> OpenAIChatCompletionsModel | None:
    return _models.get(name)
