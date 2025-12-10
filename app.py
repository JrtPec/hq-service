"""Entry point voor gecombineerde FastAPI API en Discord-bot."""

import asyncio
import os

import uvicorn
from fastapi import FastAPI

# importeer je bestaande FastAPI-app uit src/api/main.py
from src.api.main import app as api_app

# importeer bot-starter
from src.discord_service.runner import start_bot

# Exporteer één gecombineerde app voor uvicorn
app = FastAPI(title="HQ Service (API + Bot)")

# mount de bestaande API onder root (houdt je routes zoals /health, /chat, /reset)
app.mount("/", api_app)


# start Discord-bot als background task bij startup
@app.on_event("startup")
async def _startup():
    # start de bot (zorg dat env vars gezet zijn)
    asyncio.create_task(start_bot())


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
