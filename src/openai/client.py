"""OpenAI-clientconfiguratie."""

import os

import instructor

from openai import AsyncOpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = instructor.from_openai(client=AsyncOpenAI(api_key=OPENAI_API_KEY))
