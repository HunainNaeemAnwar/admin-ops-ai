import agent_system.provider

from agents import Agent, Runner, AgentOutputSchema
from pydantic import BaseModel, Field
from agent_system.provider import ACTIVE_MODEL


class EmailContent(BaseModel):
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body text")


email_writer_agent = Agent(
    name="EmailWriter",
    instructions=(
        "You write professional email content for daily production summaries. "
        "Keep it concise and professional. Address the manager respectfully."
    ),
    model=ACTIVE_MODEL,
    output_type=AgentOutputSchema(EmailContent, strict_json_schema=True),
)


async def compose_daily_email(summary_text: str) -> EmailContent:
    result = await Runner.run(
        email_writer_agent,
        input=f"Compose a daily production summary email based on this data:\n\n{summary_text}",
    )
    return result.final_output
