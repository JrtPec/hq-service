import json
from openai import AsyncOpenAI
import os

from .db import get_conversation, log_event

# ---------- Config ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

TOOLS = [
    {
        "type": "function",
        "name": "handle_event",
        "description": "Sla een gebeurtenis op in het logboek",
        "parameters": {
            "type": "object",
            "properties": {
                "mission_code": {"type": "string"},
                "event_code": {"type": "string"},
                "notes": {"type": "string"},
                "state": {
                    "type": "object",
                },
            },
            "required": ["mission_code", "event_code", "notes"],
            "additionalProperties": False,
        },
        "strict": False
    }
]

def get_system_prompt(path) -> str:
    """Lees het systeemprompt uit een bestand."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

async def chat(message: str) -> str:
    """Stuur een bericht naar het GPT-model en retourneer het antwoord."""
    system_prompt = get_system_prompt("src/game/prompts/HQ.txt")
    conversation = await get_conversation(client, "HQ", system_prompt=system_prompt)
    input_list = [{"role": "user", "content": message}]
    response = await client.responses.create(
        model=OPENAI_MODEL,
        conversation=conversation,
        input=input_list,
        tools=TOOLS,
    )

    if response.output_text != "":
        return response.output_text

    input_list = []
    for item in response.output:
        if item.type == "function_call":
            if item.name == "handle_event":
                # 3. Execute the function logic
                result = handle_event(**json.loads(item.arguments))
                
                # 4. Provide function call results to the model
                input_list.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                        "result": result
                    })
                })

    response = await client.responses.create(
        model=OPENAI_MODEL,
        conversation=conversation,
        input=input_list,
    )

    return response.output_text

def handle_event(mission_code, event_code, notes, state=None) -> dict:
    result = log_event(
        mission_code=mission_code,
        event_code=event_code,
        notes=notes,
        state=state,
    )
    return result
