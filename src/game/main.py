from openai import AsyncOpenAI
import os

from .db import get_current_conversation, reset_conversation

# ---------- Config ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def chat(message: str) -> str:
    if message == "RESET_CONVERSATION":
        conversation = await reset_conversation(client)
        return "Conversation has been reset."
    
    conversation = await get_current_conversation(client)

    response = await client.responses.create(
        model=OPENAI_MODEL,
        conversation=conversation,
        input=[{"role": "user", "content": message}],
    )

    return response.output_text
