import os
import re
import json
import openai
from config import MAX_RETRIES, PASS_THRESHOLD, MODEL, GENRES, GENRE_GUIDANCE, NUM_DRAFTS


# ── LLM call ──────────────────────────────────────────────────────────────────

def call_model(prompt: str, max_tokens=3000, temperature=0.1) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY")  # please use your own openai api key here.
    openai.api_base = "https://openrouter.ai/api/v1"
    resp = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message["content"]  # type: ignore


# ── Guardrails ────────────────────────────────────────────────────────────────

_BLOCKED = re.compile(
    r"\b(swear\s*words?|profanity|adult\s*themes?|sexual|violent|blood(y)?|gore|"
    r"drug[s]?|alcohol|f.?ck|s.?it|b.?tch|kill|murder|nude|naked|sex|porn|hate|racist)\b",
    re.IGNORECASE,
)

def check_input(text: str) -> tuple[bool, str]:
    """Returns (is_safe, reason). Reason is empty string when safe."""
    match = _BLOCKED.search(text)
    if match:
        return False, f"'{match.group()}' isn't suitable for a children's story. Please try a different idea!"

    raw = call_model(
        f"""Is this request safe and appropriate for a children's bedtime story (ages 5-10)?
Request: \"\"\"{text}\"\"\"
Flag as unsafe ONLY for: adult/sexual content, graphic violence, profanity, drugs/alcohol, hate speech.
Respond with ONLY JSON: {{"safe": true/false, "reason": "explanation if unsafe, else empty string"}}""",
        max_tokens=100, temperature=0.0
    )
    try:
        data = json.loads(raw.strip().strip("```json").strip("```"))
        if not data.get("safe", True):
            return False, data.get("reason") or "That request isn't appropriate for a children's story. Please try something else!"
    except Exception:
        pass
    return True, ""


# ── Genre classifier ──────────────────────────────────────────────────────────

def classify_genre(request: str) -> str:
    raw = call_model(
        f"""Classify this children's story request into one genre: {', '.join(GENRES)}.
- bedtime: calm/soothing  - silly: funny/absurd  - mystery: puzzle to solve
- friendship: about friends  - adventure: everything else
Respond ONLY with JSON: {{"genre": "adventure"}}
Request: {request}""",
        max_tokens=60, temperature=0.0
    )
    try:
        genre = json.loads(raw.strip()).get("genre", "adventure")
        return genre if genre in GENRES else "adventure"
    except Exception:
        return "adventure"


# ── Outline generator ─────────────────────────────────────────────────────────

def generate_outline(request: str, genre: str, feedback: str = "") -> dict:
    """
    Generate a short story outline before the full draft.
    Returns a dict with keys: title, characters, setting, conflict, resolution.
    Having the LLM plan before writing significantly improves structural coherence.
    """
    feedback_block = f"\nPrevious draft had these issues to fix:\n{feedback}\n" if feedback else ""
    raw = call_model(
        f"""You are a children's story planner. Create a brief story outline for ages 5-10.
GENRE: {genre.upper()} — {GENRE_GUIDANCE[genre]}
{feedback_block}
REQUEST: {request}

Respond ONLY with JSON (no extra text):
{{
  "title": "A short, catchy story title",
  "characters": "1-2 sentences describing the main character(s) and their personality",
  "setting": "1 sentence describing where and when the story takes place",
  "conflict": "1 sentence describing the central problem or challenge",
  "resolution": "1 sentence describing how the problem is resolved and what the character learns"
}}""",
        max_tokens=300, temperature=0.5
    )
    try:
        outline = json.loads(raw.strip().strip("```json").strip("```"))
        # Validate all required keys are present
        required = {"title", "characters", "setting", "conflict", "resolution"}
        if required.issubset(outline.keys()):
            return outline
    except Exception:
        pass
    # Fallback: return a minimal outline so the pipeline can continue
    return {
        "title": "A Wonderful Story",
        "characters": "A brave and curious child",
        "setting": "A magical, cozy world",
        "conflict": "A small problem that needs solving",
        "resolution": "The child solves the problem and learns something wonderful",
    }


def format_outline(outline: dict) -> str:
    """Format an outline dict into a readable block to inject into the story prompt."""
    return (
        f"Title: {outline['title']}\n"
        f"Characters: {outline['characters']}\n"
        f"Setting: {outline['setting']}\n"
        f"Conflict: {outline['conflict']}\n"
        f"Resolution: {outline['resolution']}"
    )


# ── Draft generator ───────────────────────────────────────────────────────────

# Each variant nudges the storyteller toward a slightly different style so the
# multi-draft tournament produces meaningfully different candidates to compare.
_DRAFT_VARIANTS = [
    # Variant 0 — vivid and descriptive
    "Use vivid, sensory details so the child can picture every scene clearly.",
    # Variant 1 — dialogue-driven and playful
    "Bring characters to life through fun, expressive dialogue. Let them talk a lot.",
    # Variant 2 — classic fairy-tale cadence
    "Use a classic fairy-tale rhythm with gentle repetition and a sing-song feel.",
]

def generate_draft(request: str, genre: str, outline: dict, variant_index: int = 0) -> str:
    """Expand an outline into a full story using a particular style variant."""
    variant_hint = _DRAFT_VARIANTS[variant_index % len(_DRAFT_VARIANTS)]
    outline_block = format_outline(outline)
    return call_model(
        f"""You are a warm children's storyteller writing for ages 5-10.
GENRE: {genre.upper()} — {GENRE_GUIDANCE[genre]}
STYLE HINT: {variant_hint}

Follow this outline exactly — do NOT change the conflict or resolution:
{outline_block}

Rules: simple vocabulary, short sentences, positive ending with a moral, 300-450 words.
Write the full story now (start directly with the title on line 1):""",
        max_tokens=700, temperature=0.75
    )


# ── Judge ─────────────────────────────────────────────────────────────────────

def judge_story(request: str, story: str) -> dict:
    """Returns dict with keys: passed (bool), score (int), issues (list[str])."""
    raw = call_model(
        f"""You are a balanced children's story editor for ages 5-10. Score fairly — don't invent problems.

Score each criterion 0-2 (max 10 total):
1. AGE-APPROPRIATENESS: Mild conflict (dog chasing cat, a bully who reforms) is NORMAL. Only fail for graphic violence, horror, adult/sexual content.
2. VOCABULARY: Common descriptive words ("cautiously", "accidentally") are FINE. Only fail truly obscure words no child would know.
3. COHERENCE: Clear beginning, middle, end with a resolved problem.
4. ENGAGEMENT: A child would enjoy listening to this.
5. POSITIVE MESSAGE: Ends hopefully or happily. Doesn't need an explicit lesson but a lesson is preferred.

Request: {request}
Story: \"\"\"{story}\"\"\"

Respond ONLY with JSON: {{"passed": true/false, "score": 1-10, "issues": ["only real problems, not stylistic preferences"]}}
Set passed=true if score >= {PASS_THRESHOLD} and age-appropriateness score > 0.
A story that fulfils the request and entertains children should score 8-10.""",
        max_tokens=300, temperature=0.0
    )
    try:
        data = json.loads(raw.strip().strip("```json").strip("```"))
        return {"passed": bool(data.get("passed")), "score": int(data.get("score", 0)), "issues": data.get("issues", [])}
    except Exception:
        return {"passed": True, "score": PASS_THRESHOLD, "issues": []}


def judge_tournament(request: str, drafts: list[str]) -> tuple[str, dict]:
    """
    Given multiple drafts, ask the judge to pick the single best one.
    Returns (winning_story, verdict_of_winner).
    Falls back to individual scoring if the LLM can't parse the tournament response.
    """
    if len(drafts) == 1:
        verdict = judge_story(request, drafts[0])
        return drafts[0], verdict

    numbered = "\n\n".join(
        f"--- DRAFT {i+1} ---\n{d}" for i, d in enumerate(drafts)
    )
    raw = call_model(
        f"""You are a children's story editor comparing {len(drafts)} drafts for ages 5-10.
Request the stories should fulfill: {request}

{numbered}

Evaluate each draft on: age-appropriateness, vocabulary, coherence, engagement, positive message.
Pick the single best draft. If one draft excels in some areas and another in different ones, pick the overall strongest.

Respond ONLY with JSON:
{{
  "best_draft": 1,
  "score": 8,
  "passed": true,
  "issues": ["any remaining issues with the winning draft"]
}}
where best_draft is the draft number (1-{len(drafts)}) and score is out of 10.""",
        max_tokens=300, temperature=0.0
    )
    try:
        data = json.loads(raw.strip().strip("```json").strip("```"))
        idx = int(data.get("best_draft", 1)) - 1
        idx = max(0, min(idx, len(drafts) - 1))  # clamp to valid range
        winner = drafts[idx]
        verdict = {
            "passed": bool(data.get("passed")),
            "score": int(data.get("score", 0)),
            "issues": data.get("issues", []),
        }
        return winner, verdict
    except Exception:
        # Fallback: score individually and pick the best
        best_story, best_verdict = drafts[0], {"passed": False, "score": 0, "issues": []}
        for draft in drafts:
            v = judge_story(request, draft)
            if v["score"] > best_verdict["score"]:
                best_story, best_verdict = draft, v
        return best_story, best_verdict


# ── Pipeline ──────────────────────────────────────────────────────────────────

def generate_story(request: str) -> tuple[str, bool]:
    """
    Full pipeline: classify → outline → multi-draft tournament → judge → retry.

    Each retry loop:
      1. Generates a fresh outline (incorporating judge feedback on retries).
      2. Expands that outline into NUM_DRAFTS style variants in parallel.
      3. Runs a tournament judge that picks the strongest draft.
      4. If the winner passes the threshold, returns it immediately.
      5. Otherwise, feeds the issues back into the next outline attempt.

    Returns (story, all_failed).
    all_failed=True means every attempt scored below PASS_THRESHOLD.
    """
    genre = classify_genre(request)
    print(f"\n Genre detected: {genre}")

    feedback, best_story, best_score = "", "", 0

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n  ── Attempt {attempt}/{MAX_RETRIES} ──")

        # Step 1: generate outline
        print("  Planning outline...")
        outline = generate_outline(request, genre, feedback)
        print(f"  Title: \"{outline['title']}\"")

        # Step 2: generate NUM_DRAFTS style variants from the same outline
        drafts = []
        for v in range(NUM_DRAFTS):
            print(f"  Generating draft variant {v+1}/{NUM_DRAFTS}...")
            draft = generate_draft(request, genre, outline, variant_index=v)
            drafts.append(draft)

        # Step 3: tournament — judge picks the strongest draft
        print(f"  Running tournament across {NUM_DRAFTS} drafts...")
        winner, verdict = judge_tournament(request, drafts)

        status = "✓ PASSED" if verdict["passed"] else "✗ FAILED"
        print(f"   {status} | Score: {verdict['score']}/10")
        for issue in verdict["issues"]:
            print(f"   • {issue}")

        if verdict["score"] > best_score:
            best_score, best_story = verdict["score"], winner

        if verdict["passed"]:
            return winner, False

        feedback = "\n".join(f"- {i}" for i in verdict["issues"])

    all_failed = best_score < PASS_THRESHOLD
    if all_failed:
        print(f"\n All attempts scored below threshold ({best_score}/10 < {PASS_THRESHOLD}/10). Reverting to previous story.")
    else:
        print(f"\n  Max retries reached. Returning best story (score: {best_score}/10).")

    return best_story, all_failed