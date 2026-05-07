"""
prompt_builder.py — Assembles the full storyteller prompt.

Combines genre guidance, age-appropriateness rules, story arc structure,
and optional judge feedback into a single prompt string.
"""

from config import GENRE_GUIDANCE


def build_story_prompt(user_request: str, genre: str, feedback: str = "") -> str:
    """
    Build the storyteller prompt for a given request and genre.

    Args:
        user_request: The original (or revised) story request from the user.
        genre:        Detected genre string (must be a key in GENRE_GUIDANCE).
        feedback:     Judge feedback from the previous attempt, if any.
                      When non-empty, a revision instruction block is appended.

    Returns:
        A fully-formed prompt string ready to pass to call_model().
    """
    genre_tip = GENRE_GUIDANCE.get(genre, GENRE_GUIDANCE["adventure"])

    revision_block = ""
    if feedback:
        revision_block = f"""
A previous draft was reviewed and needs these improvements:
{feedback}

Please rewrite the story fully, addressing every point above.
"""

    return f"""You are a warm, imaginative children's storyteller writing for ages 5 to 10.

GENRE: {genre.upper()}
{genre_tip}

STORY STRUCTURE — follow this three-act arc:
1. Setup   — introduce the main character and their world
2. Conflict — a problem or challenge appears
3. Resolution — the character solves it and learns something positive

LANGUAGE RULES:
- Use simple vocabulary (words a 6-year-old could understand)
- Keep sentences short and easy to read aloud
- Include vivid but age-appropriate descriptions
- End on a positive, uplifting note
- Target length: 300–450 words

STORY REQUEST: {user_request}
{revision_block}
Write the story now:"""
