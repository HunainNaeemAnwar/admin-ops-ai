import agent_system.provider

from agents import Agent, Runner, AgentOutputSchema
from pydantic import BaseModel, Field
from config import GEMINI_MODEL


class ExtractedProduct(BaseModel):
    product_code: str = Field(description="Product code from catalog (e.g., BOLT-10x20, NUT-STD)")
    quantity: int = Field(description="Number of pieces completed", ge=1)


class ExtractionOutput(BaseModel):
    worker: str = Field(description="Worker name")
    products: list[ExtractedProduct] = Field(description="List of products and quantities")


extraction_agent = Agent(
    name="DataExtractor",
    instructions=(
        "You extract structured work data from natural language text. "
        "The user describes what a worker produced today. "
        "Identify the worker name, each product type, and quantity for each. "
        "Product codes are like BOLT-10x20, BOLT-6x25, BOLT-6x30, NUT-STD, NUT-M10 etc. "
        "Map descriptions like '10*20 bolt' to 'BOLT-10x20', 'nut' to 'NUT-STD', "
        "'6*25 bolt' to 'BOLT-6x25', '6*30 bolt' to 'BOLT-6x30'. "
        "If the worker name is not clear, use 'Unknown'."
    ),
    model=GEMINI_MODEL,
    output_type=AgentOutputSchema(ExtractionOutput, strict_json_schema=True),
)


async def extract_from_text(text: str) -> ExtractionOutput:
    result = await Runner.run(extraction_agent, input=text)
    return result.final_output
