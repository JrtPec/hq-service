"""Models voor GPT Chat Service API."""

from pydantic import BaseModel


# ---------- Models ----------
class ChatRequest(BaseModel):
    """Request model for chat messages."""

    message: str


class ChatResponse(BaseModel):
    """Response model for chat replies."""

    reply: str
