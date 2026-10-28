import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

config = {
    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "api_key": os.environ["OPENAI_API_KEY"],
}

base_url = os.getenv("OPENAI_BASE_URL")
if base_url:
    config["base_url"] = base_url

model = ChatOpenAI(**config)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a concise AI assistant."),
    ("human", "Explain {topic} in three bullet points."),
])

parser = StrOutputParser()

chain = prompt | model | parser

result = chain.invoke({
    "topic": "Retrieval-Augmented Generation"
})

print(result)