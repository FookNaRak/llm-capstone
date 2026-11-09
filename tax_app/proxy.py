"""Configuration for the course LLM proxy."""

import os
from pathlib import Path

MODEL = "gemma-4-E4B-it"

class ProxyConfigurationError(RuntimeError):
    """The environment lacks the credentials for the course proxy."""


def _proxy_client():
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    if not all(os.getenv(name, "").strip() for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL")):
        raise ProxyConfigurationError("Set OPENAI_API_KEY and OPENAI_BASE_URL in .env.")
    return OpenAI(timeout=30.0, max_retries=0)
