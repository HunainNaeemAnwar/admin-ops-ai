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

# Tracing key — real OpenAI API key for Traces dashboard
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

# Cerebras LLM client
cerebras_client = AsyncOpenAI(
    api_key=CEREBRAS_API_KEY,
    base_url=DEFAULT_OPENAI_BASE_URL,
)

cerebras_model = OpenAIChatCompletionsModel(
    model=CEREBRAS_MODEL,
    openai_client=cerebras_client,
)

# Gemini LLM client
gemini_client = AsyncOpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

gemini_model = OpenAIChatCompletionsModel(
    model=GEMINI_MODEL,
    openai_client=gemini_client,
)

# Mistral LLM client
mistral_client = AsyncOpenAI(
    api_key=MISTRAL_API_KEY,
    base_url=MISTRAL_BASE_URL,
)

mistral_model = OpenAIChatCompletionsModel(
    model=MISTRAL_MODEL,
    openai_client=mistral_client,
)

# OpenAI direct client (uses the tracing key)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

openai_model = OpenAIChatCompletionsModel(
    model="gpt-4o-mini",
    openai_client=openai_client,
)

# Active model — selected by LLM_PROVIDER env var
ACTIVE_MODEL = mistral_model
if LLM_PROVIDER == "cerebras":
    ACTIVE_MODEL = cerebras_model
elif LLM_PROVIDER == "gemini":
    ACTIVE_MODEL = gemini_model
elif LLM_PROVIDER == "openai":
    ACTIVE_MODEL = openai_model

# Fallback chain: if the active model fails (429, tool issues), try these in order
ALL_MODELS: list[OpenAIChatCompletionsModel] = [mistral_model, gemini_model, cerebras_model, openai_model]


def get_model_by_name(name: str) -> OpenAIChatCompletionsModel:
    if name == "mistral":
        return mistral_model
    elif name == "gemini":
        return gemini_model
    elif name == "cerebras":
        return cerebras_model
    elif name == "openai":
        return openai_model
    return ACTIVE_MODEL
