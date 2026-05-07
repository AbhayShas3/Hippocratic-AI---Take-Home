"""
classifier.py — Genre classifier agent.

Buckets a story request into one of the supported genres so the
storyteller can apply genre-specific guidance.
"""

import json
from llm_client import call_model
from config import GENRES

_PROMPT_TEMPLATE = """You are a story genre classifier for children aged 5-10.
Given a story request, classify it into exactly one of these genres: {genres}.

Rules:
- 'bedtime': calm, soothing, good for falling asleep
- 'silly': funny, absurd, lots of jokes and wordplay
- 'mystery': a puzzle or secret to solve
- 'friendship': about making or keeping friends
- 'adventure': everything else — action, exploration, quests

Respond with ONLY a JSON object like: {{"genre": "adventure"}}

Story request: {request}"""


def classify_genre(user_request: str) -> str:
    """
    Returns a genre string for the given request.
    Falls back to 'adventure' if the LLM response can't be parsed.
    """
    prompt = _PROMPT_TEMPLATE.format(
        genres=", ".join(GENRES),
        request=user_request,
    )
    raw = call_model(prompt, max_tokens=60, temperature=0.0)
    try:
        data = json.loads(raw.strip())
        genre = data.get("genre", "adventure")
        return genre if genre in GENRES else "adventure"
    except (json.JSONDecodeError, AttributeError):
        return "adventure"
