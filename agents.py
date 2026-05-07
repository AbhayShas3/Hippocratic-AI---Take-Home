import os
import re
import json
import openai
from config import MAX_RETRIES, PASS_THRESHOLD, MODEL, GENRES, GENRE_GUIDANCE


# ── LLM call ──────────────────────────────────────────────────────────────────

def call_model(prompt: str, max_tokens=3000, temperature=0.1) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY") # please use your own openai api key here.
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
5. POSITIVE MESSAGE: Ends hopefully or happily. Doesn't need an explicit lesson.

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


# ── Pipeline ──────────────────────────────────────────────────────────────────

def generate_story(request: str) -> tuple[str, bool]:
    """
    Full pipeline: classify → generate → judge → retry.
    Returns (story, all_failed).
    all_failed=True means every draft scored below PASS_THRESHOLD — caller should keep the previous story.
    """
    genre = classify_genre(request)
    print(f"\n Genre detected: {genre}")

    feedback, best_story, best_score = "", "", 0

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"  Generating draft {attempt}/{MAX_RETRIES}...")

        story = call_model(
            f"""You are a warm children's storyteller writing for ages 5-10.
GENRE: {genre.upper()} — {GENRE_GUIDANCE[genre]}
Follow a 3-act arc: setup → conflict → resolution. Simple vocabulary, short sentences, positive ending. 300-450 words.
{"Previous draft had issues:\\n" + feedback if feedback else ""}
REQUEST: {request}
Write the story now:""",
            max_tokens=700, temperature=0.75
        )

        print(" Judging draft...")
        verdict = judge_story(request, story)
        status = " PASSED" if verdict["passed"] else " FAILED"
        print(f"   {status} | Score: {verdict['score']}/10")
        for issue in verdict["issues"]:
            print(f"   • {issue}")

        if verdict["score"] > best_score:
            best_score, best_story = verdict["score"], story

        if verdict["passed"]:
            return story, False

        feedback = "\n".join(f"- {i}" for i in verdict["issues"])

    all_failed = best_score < PASS_THRESHOLD
    if all_failed:
        print(f"\n All drafts scored below threshold ({best_score}/10 < {PASS_THRESHOLD}/10). Reverting to previous story.")
    else:
        print(f"\n  Max retries reached. Best score: {best_score}/10")

    return best_story, all_failed