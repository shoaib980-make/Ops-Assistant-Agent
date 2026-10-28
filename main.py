
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

load_dotenv()


# 1. Define the output schema
class ExtractedInfo(BaseModel):
    title: str = Field(
        description="A short, descriptive title"
    )
    summary: str = Field(
        description="A concise summary of the input"
    )
    category: str = Field(
        description="The main subject category"
    )
    keywords: list[str] = Field(
        description="Three to five relevant keywords"
    )


# 2. Configure the chat model
config = {
    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "api_key": os.environ["OPENAI_API_KEY"],
    "temperature": 0,
}

base_url = os.getenv("OPENAI_BASE_URL")
if base_url:
    config["base_url"] = base_url

model = ChatOpenAI(**config)


# 3. Create the output parser
parser = PydanticOutputParser(
    pydantic_object=ExtractedInfo
)


# 4. Define a reusable prompt
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        You are a professional information extraction assistant.

        Extract information only from the supplied text.
        Do not invent names, facts, or details.
        If information is missing, use a brief honest description
        rather than inventing a value.

        Follow these formatting instructions:
        {format_instructions}
        """
    ),
    (
        "human",
        "Extract structured information from this text:\n{text}"
    ),
])


# 5. Compose the LCEL chain
chain = prompt | model | parser


# 6. Execute the chain
def extract_information(text: str) -> ExtractedInfo:
    if not text.strip():
        raise ValueError("Input text cannot be empty.")

    return chain.invoke({
        "text": text,
        "format_instructions": parser.get_format_instructions(),
    })


if __name__ == "__main__":
    sample_text = """
    TaskFlow is a task management application built using
    FastAPI, PostgreSQL, and JavaScript. It allows users
    to organize tasks and track their progress.
    """

    result = extract_information(sample_text)

    print(result.model_dump_json(indent=2))