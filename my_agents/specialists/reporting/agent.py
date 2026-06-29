from agents import Agent, ModelSettings
from my_agents.utils import load_prompt
from tools.get_daily_status import get_daily_status_tool
from tools.get_summary import get_summary_tool
from tools.send_report import send_report_tool
from tools.list_catalog import list_catalog_tool


def create_agent(model, model_settings: ModelSettings | None = None, worker_list: str = "", today_date: str = "", output_guardrails: list | None = None) -> Agent:
    if model_settings is None:
        model_settings = ModelSettings(temperature=0.3, top_p=0.9, max_tokens=2000, parallel_tool_calls=True)

    def _instructions(ctx, agent):
        return load_prompt("reporting.md", {"WORKER_LIST": worker_list, "TODAY_DATE": today_date})

    return Agent(
        name="ReportingAgent",
        instructions=_instructions,
        model=model,
        model_settings=model_settings,
        output_guardrails=output_guardrails or [],
        tools=[
            get_daily_status_tool,
            get_summary_tool,
            send_report_tool,
            list_catalog_tool,
        ],
    )
