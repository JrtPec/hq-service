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
        "description": "Maak een nieuwe deelnemer aan in het systeem of overschrijf een bestaande deelnemer.",
        "parameters": Participant.tool_schema(),
    },
    {
        "type": "function",
        "name": "get_participant",
        "description": "Haal een deelnemer op basis van de naam.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "De naam van de deelnemer.",
                },
            },
            "required": ["name"],
        },
        "return_schema": Participant.tool_schema(),
    },
    {
        "type": "function",
        "name": "get_all_participants",
        "description": "Haal alle deelnemers op.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
        "return_schema": {
            "type": "array",
            "items": Participant.tool_schema(),
        },
    },
    {
        "type": "function",
        "name": "get_logs",
        "description": "Haal de laatste N logberichten op.",
        "parameters": {
            "type": "object",
            "properties": {
                "top_n": {
                    "type": "integer",
                    "description": "Het aantal logberichten om op te halen.",
                    "default": 10,
                },
            },
            "required": [],
        },
        "return_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ts": {"type": "string", "description": "Timestamp van het logbericht."},
                    "sender": {"type": "string", "description": "Afzender van het bericht."},
                    "content": {"type": "string", "description": "Inhoud van het bericht."},
                },
            },
        },
    },
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
            func = globals().get(item.name)
            if func:
                result = await func(**json.loads(item.arguments))
                input_list.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result,
                })

    response = await client.responses.create(
        model=OPENAI_MODEL,
        conversation=HQ.conversation_id,
        input=input_list,  # type: ignore
    )
    if response.output_text != "":
        return response.output_text

    return None

async def create_participant(**kwargs) -> str:
    """Maak een nieuwe deelnemer aan."""
    participant = Participant.model_validate(kwargs)
    participant = typing.cast(Participant, participant)
    participant.save()
    return participant.model_dump_json(ensure_ascii=False)

async def get_participant(name: str) -> str:
    """Haal een deelnemer op basis van de naam."""
    try:
        participant = Participant.load(name)
        return participant.model_dump_json(ensure_ascii=False)
    except FileNotFoundError:
        return "Deelnemer niet gevonden."
    
async def get_all_participants() -> str:
    """Haal alle deelnemers op."""
    participants = Participant.load_all()
    if not participants:
        return "Er zijn geen deelnemers gevonden."
    participants = [participant.model_dump_json(ensure_ascii=False) for participant in participants]
    return json.dumps(participants, ensure_ascii=False)

async def get_logs(top_n: int = 10) -> str:
    """Haal de laatste N logberichten op."""
    log_path = "data/game_log.jsonl"
    if not os.path.exists(log_path):
        return "Er zijn geen logberichten gevonden."
    
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    last_lines = lines[-top_n:]
    return "[" + ",".join(line.strip() for line in last_lines) + "]"