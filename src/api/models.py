from pydantic import BaseModel

# ---------- Models ----------
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str