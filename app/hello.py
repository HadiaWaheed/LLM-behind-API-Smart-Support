import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

base_url = os.getenv("LLM_BASE_URL")
api_key = os.getenv("LLM_API_KEY")
model = os.getenv("LLM_MODEL")


if not base_url:
    raise ValueError("LLM_BASE_URL is missing from .env")

if not api_key:
    raise ValueError("LLM_API_KEY is missing from .env")

if not model:
    raise ValueError("LLM_MODEL is missing from .env")


client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)


response = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": "Reply with exactly one word: ready",
        }
    ],
    temperature=0,
)

print(response.choices[0].message.content)