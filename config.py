"""
config.py — Central constants and configuration for the story generator.
"""

# Model settings
MODEL = "gpt-3.5-turbo"
API_BASE = "https://openrouter.ai/api/v1"   # Switch to None to use OpenAI directly

# Pipeline tuning
MAX_RETRIES = 3          # Max judge → rewrite cycles per story generation
PASS_THRESHOLD = 7       # Judge score (out of 10) required to pass

# Supported genres
GENRES = ["adventure", "bedtime", "silly", "mystery", "friendship"]

# Per-genre storytelling tips injected into the storyteller prompt
GENRE_GUIDANCE = {
    "adventure":  "Include a brave hero, a clear quest or goal, one obstacle to overcome, and a triumphant ending.",
    "bedtime":    "Use a slow, gentle pace. Describe cozy settings. End with the character drifting peacefully to sleep.",
    "silly":      "Add funny misunderstandings, silly names, and at least one joke or humorous moment kids will giggle at.",
    "mystery":    "Introduce a small mystery or puzzle early on, give clues throughout, and reveal the answer at the end.",
    "friendship": "Focus on characters learning to understand each other. Emphasise kindness, sharing, and empathy.",
}
