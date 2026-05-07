"""
guardrails.py — Safety agent that screens user input and revision requests
before any story generation begins.

Two layers of defence:
  1. Rule-based fast check  — instant, no API call, catches obvious keywords.
  2. LLM-based deep check   — catches subtle or reworded inappropriate requests.

Returns a GuardrailResult dataclass so callers can branch cleanly without
parsing strings.
"""

import re
from dataclasses import dataclass
from llm_client import call_model

# ── Rule-based blocklist ──────────────────────────────────────────────────────
# Catches the most obvious cases instantly without spending an API call.

_BLOCKED_PATTERNS = [
    r"\bswear\s*words?\b",
    r"\bprofanity\b",
    r"\bcurse\s*words?\b",
    r"\badult\s*themes?\b",
    r"\bsexual\b",
    r"\bviolent\b",
    r"\bblood(y|ier)?\b",
    r"\bgore\b",
    r"\bdrug[s]?\b",
    r"\balcohol\b",
    r"\bf.?ck\b",
    r"\bs.?it\b",
    r"\bb.?tch\b",
    r"\bass\b",
    r"\bdamn\b",
    r"\bhell\b",
    r"\bkill\b",
    r"\bmurder\b",
    r"\bdeath\b",
    r"\bnude\b",
    r"\bnaked\b",
    r"\bsex\b",
    r"\bporn\b",
    r"\berotic\b",
    r"\bhate\b",
    r"\bracist\b",
]

_BLOCKED_RE = re.compile("|".join(_BLOCKED_PATTERNS), re.IGNORECASE)


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class GuardrailResult:
    safe: bool
    reason: str   # Human-readable explanation (shown to user when blocked)


# ── Public API ────────────────────────────────────────────────────────────────

def check_input(text: str) -> GuardrailResult:
    """
    Screen `text` (a story request or revision instruction) for inappropriate
    content. Returns a GuardrailResult with safe=True if the text is fine,
    or safe=False with a reason if it should be blocked.

    Fast path: rule-based keyword scan.
    Slow path: LLM judge for anything the keyword scan misses.
    """
    # ── Layer 1: keyword scan ─────────────────────────────────────────────────
    match = _BLOCKED_RE.search(text)
    if match:
        return GuardrailResult(
            safe=False,
            reason=(
                f"Your request contains content that isn't suitable for a children's "
                f"story (detected: '{match.group()}'). Please try a different idea!"
            ),
        )

    # ── Layer 2: LLM guardrail ────────────────────────────────────────────────
    return _llm_safety_check(text)


# ── Internal helpers ──────────────────────────────────────────────────────────

_LLM_GUARDRAIL_PROMPT = """You are a content safety agent for a children's bedtime story app (ages 5-10).

Your job is to decide whether the following user request is safe and appropriate
for generating a children's story. Flag it as UNSAFE if it asks for:
- Adult, sexual, or romantic content
- Violence, gore, or horror
- Profanity or swear words
- Drug, alcohol, or substance references
- Hate speech, discrimination, or bullying glorification
- Anything else clearly inappropriate for a 5-10 year old

User request:
\"\"\"
{text}
\"\"\"

Respond with ONLY a JSON object:
{{
  "safe": true or false,
  "reason": "brief explanation if unsafe, empty string if safe"
}}"""


def _llm_safety_check(text: str) -> GuardrailResult:
    """Call the LLM to do a deeper semantic safety check."""
    import json

    prompt = _LLM_GUARDRAIL_PROMPT.format(text=text)
    try:
        raw = call_model(prompt, max_tokens=120, temperature=0.0)
        # Strip possible markdown fences
        clean = raw.strip().strip("```json").strip("```").strip()
        data = json.loads(clean)
        safe = bool(data.get("safe", True))
        reason = data.get("reason", "")
        if not safe:
            return GuardrailResult(
                safe=False,
                reason=(
                    reason
                    or "Your request doesn't seem appropriate for a children's story. Please try something else!"
                ),
            )
        return GuardrailResult(safe=True, reason="")
    except Exception:
        # If the safety check itself errors, fail open (allow) to avoid
        # blocking legitimate requests due to transient API issues.
        return GuardrailResult(safe=True, reason="")
