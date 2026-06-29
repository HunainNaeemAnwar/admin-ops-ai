from agents import Agent, ModelSettings
from my_agents.utils import load_prompt
from tools.log_rejection import log_rejection_tool
from tools.record_advance import record_advance_tool
from tools.generate_payslip import generate_payslip_tool


def create_agent(model, model_settings: ModelSettings | None = None, worker_list: str = "", today_date: str = "") -> Agent:
    if model_settings is None:
        model_settings = ModelSettings(temperature=0.3, top_p=0.9, max_tokens=2000, parallel_tool_calls=True)

    def _instructions(ctx, agent):
        return load_prompt("finance.md", {"WORKER_LIST": worker_list, "TODAY_DATE": today_date})

    return Agent(
        name="FinanceAgent",
        instructions=_instructions,
        model=model,
        model_settings=model_settings,
        tools=[
            log_rejection_tool,
            record_advance_tool,
            generate_payslip_tool,
        ],
    )
