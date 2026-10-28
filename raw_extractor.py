
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

config = {
    "api_key": os.environ["OPENAI_API_KEY"],
}

base_url = os.getenv("OPENAI_BASE_URL")
if base_url:
    config["base_url"] = base_url

client = OpenAI(**config)

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def extract_information(text: str) -> dict:
    if not text.strip():
        raise ValueError("Input text cannot be empty.")

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """
                Extract a title, summary, category, and
                three to five keywords from the input.
                Return valid JSON with these four fields.
                Do not invent missing facts.
                """
            },
            {
                "role": "user",
                "content": text,
            },
        ],
        response_format={"type": "json_object"},
    )

    result = json.loads(
        response.choices[0].message.content
    )

    required = {"title", "summary", "category", "keywords"}
    if set(result) != required:
        raise ValueError("Unexpected output fields.")

    if not all(
        isinstance(result[key], str)
        for key in ("title", "summary", "category")
    ):
        raise ValueError("Invalid field types.")

    if not (
        isinstance(result["keywords"], list)
        and all(isinstance(k, str) for k in result["keywords"])
    ):
        raise ValueError("Keywords must be a list of strings.")

    return result


if __name__ == "__main__":
    text = (
        "TaskFlow is a task management application built "
        "with FastAPI and PostgreSQL."
    )

    print(json.dumps(
        extract_information(text),
        indent=2
    ))
