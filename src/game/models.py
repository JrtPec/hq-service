from pathlib import Path
import instructor
from instructor import OpenAISchema
from typing import Literal

def get_system_prompt(path) -> str:
    """Lees het systeemprompt uit een bestand."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

class Participant(OpenAISchema):
    name: str
    role: Literal["player", "bot"]
    notes: str | None = None

    class Config:
        extra = "allow"

    def save(self):
        """Sla de configuratie op."""
        participant_path = Path("data") / "participants" / f"{self.name}.json"
        participant_path.parent.mkdir(parents=True, exist_ok=True)
        with open(participant_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2, ensure_ascii=False))

    @classmethod
    def tool_schema(cls) -> dict:
        schema = cls.model_json_schema(mode="serialization")
        schema.pop("title", None)
        schema.pop("$defs", None)
        return schema

class Bot(Participant):
    system_prompt: str
    conversation_id: str | None = None
    role: Literal["bot"] = "bot"

    async def ensure_conversation(self, client: instructor.AsyncInstructor):
        if not self.conversation_id:
            conv = await client.conversations.create(
                items=[{"role": "system", "content": self.system_prompt}],
            )
            self.conversation_id = conv.id
            self.save()
