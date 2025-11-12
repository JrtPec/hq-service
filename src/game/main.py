import json
import typing
from openai import AsyncOpenAI
import os
from .models import Bot, get_system_prompt, Participant
import instructor

# ---------- Config ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

client = instructor.from_openai(client=AsyncOpenAI(api_key=OPENAI_API_KEY))

HQ = Bot(
    name="HQ",
    system_prompt=get_system_prompt("src/game/prompts/HQ.txt"),
)
HQ.save()

TOOLS = [
    {
        "type": "function",
        "name": "create_participant",
        "description": "Maak een nieuwe deelnemer aan in het systeem",
        "parameters": Participant.tool_schema(),
    }
]

async def chat(message: str) -> str | None:
    """Stuur een bericht naar het GPT-model en retourneer het antwoord."""
    await HQ.ensure_conversation(client)
    input_list = [{"role": "user", "content": message}]
    response = await client.responses.create(
        model=OPENAI_MODEL,
        conversation=HQ.conversation_id,
        input=input_list,  # type: ignore
        tools=TOOLS,  # type: ignore
    )

    if response.output_text != "":
        return response.output_text
    
    for item in response.output:
        if item.type == "function_call":
            if item.name == "create_participant":
                participant = await create_participant(item.arguments)
                input_list.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": participant.model_dump_json(ensure_ascii=False),
                })

    response = await client.responses.create(
        model=OPENAI_MODEL,
        conversation=HQ.conversation_id,
        input=input_list,  # type: ignore
    )
    if response.output_text != "":
        return response.output_text

    return None

async def create_participant(args) -> Participant:
    """Maak een nieuwe deelnemer aan."""
    participant = Participant.model_validate_json(args)
    participant = typing.cast(Participant, participant)
    participant.save()
    return participant
