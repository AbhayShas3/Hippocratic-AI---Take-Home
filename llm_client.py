"""
llm_client.py — Thin wrapper around the OpenAI/OpenRouter API call.

Keeping this isolated means swapping the underlying provider only
requires changes here, not throughout the codebase.
"""

import os
import openai
from config import MODEL, API_BASE


def call_model(prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> str:
    """
    Send a single-turn prompt to the LLM and return the text response.

    Uses OpenRouter if API_BASE is set, otherwise falls back to OpenAI directly.
    API key is read from the environment:
      - OPENROUTER_API_KEY  (when using OpenRouter)
      - OPENAI_API_KEY      (when using OpenAI directly)
    """
    if API_BASE:
        openai.api_key = os.getenv("OPENROUTER_API_KEY")
        openai.api_base = API_BASE
    else:
        openai.api_key = os.getenv("OPENAI_API_KEY")

    extra_headers = (
        {
            "HTTP-Referer": "http://localhost",
            "X-Title": "Bedtime Story Generator",
        }
        if API_BASE
        else {}
    )

    resp = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        max_tokens=max_tokens,
        temperature=temperature,
        headers=extra_headers,
    )
    return resp.choices[0].message["content"]  # type: ignore
