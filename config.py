MAX_RETRIES    = 3
PASS_THRESHOLD = 7
MODEL          = "gpt-3.5-turbo"
NUM_DRAFTS     = 3   # number of style variants generated per outline in the tournament

GENRES = ["adventure", "bedtime", "silly", "mystery", "friendship"]

GENRE_GUIDANCE = {
    "adventure":  "Include a brave hero, a clear quest, one obstacle, and a triumphant ending.",
    "bedtime":    "Use a slow, gentle pace with cozy settings. End with the character drifting to sleep.",
    "silly":      "Add funny misunderstandings, silly names, and at least one joke kids will giggle at.",
    "mystery":    "Introduce a small mystery early on, give clues throughout, and reveal the answer at the end.",
    "friendship": "Focus on characters learning to understand each other through kindness and empathy.",
}