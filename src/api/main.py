import os
from fastapi import FastAPI, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyQuery, APIKeyHeader
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import ChatRequest, ChatResponse
from ..game.main import chat as game_chat

# ---------- Config ----------
API_KEYS: list[str] = os.getenv("API_KEYS", "").split(",")  # comma separated
api_key_query = APIKeyQuery(name="api-key", auto_error=False)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

# ---------- App Init ----------
app = FastAPI(title="GPT Chat Service", version="0.1.0")
security = HTTPBearer(auto_error=False)

# --------- Middleware ----------
# CORS (pas origins aan of laat leeg voor lokaal)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],  # in productie: beperk!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_api_key(
    bearer: HTTPAuthorizationCredentials = Security(security),
    api_key_header: str = Security(api_key_header),
    api_key_query: str = Security(api_key_query),
) -> str:
    """Validate API key or bearer token."""
    token = None
    if bearer:
        token = bearer.credentials
    elif api_key_header:
        token = api_key_header
    elif api_key_query:
        token = api_key_query

    if not token:
        raise HTTPException(status_code=401, detail="Missing API Key")

    if token not in API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    return token


@app.get("/health")
async def health():
    """Simple health check."""
    return {"ok": True}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, api_key: str = Security(get_api_key)):
    """Send a message to the GPT model and return the response."""
    reply = await game_chat(req.message)
    return ChatResponse(reply=reply)
