from agents import Agent, ModelSettings
from my_agents.utils import load_prompt
from tools.log_production import log_production_tool
from tools.parse_table import parse_table_tool
from tools.mark_absent import mark_absent_tool
from tools.update_entry import update_entry_tool
from tools.batch_daily_update import batch_daily_update_tool


def create_agent(model, model_settings: ModelSettings | None = None, worker_list: str = "", today_date: str = "") -> Agent:
    if model_settings is None:
        model_settings = ModelSettings(temperature=0.2, top_p=0.9, max_tokens=2000, parallel_tool_calls=True)

    def _instructions(ctx, agent):
        return load_prompt("production.md", {"WORKER_LIST": worker_list, "TODAY_DATE": today_date})

    return Agent(
        name="ProductionAgent",
        instructions=_instructions,
        model=model,
        model_settings=model_settings,
        tools=[
            log_production_tool,
            parse_table_tool,
            mark_absent_tool,
            update_entry_tool,
            batch_daily_update_tool,
        ],
    )
