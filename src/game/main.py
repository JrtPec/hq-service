from openai import AsyncOpenAI
import os

from .db import get_conversation

# ---------- Config ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

def get_system_prompt(path) -> str:
    """Lees het systeemprompt uit een bestand."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

async def chat(message: str) -> str:
    """Stuur een bericht naar het GPT-model en retourneer het antwoord."""
    system_prompt = get_system_prompt("src/game/prompts/HQ.txt")
    conversation = await get_conversation(client, "HQ", system_prompt=system_prompt)
    response = await client.responses.create(
        model=OPENAI_MODEL,
        conversation=conversation,
        input=[{"role": "user", "content": message}],
    )

    return response.output_text
