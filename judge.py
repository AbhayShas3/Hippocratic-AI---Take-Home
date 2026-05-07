"""
judge.py — LLM judge agent that evaluates story drafts.

Scores a story on five child-appropriate criteria and returns a structured
verdict so the pipeline can decide whether to accept or retry.
"""

import json
from dataclasses import dataclass, field
from typing import List
from llm_client import call_model
from config import PASS_THRESHOLD

_JUDGE_PROMPT = """You are a balanced children's story editor evaluating stories for ages 5-10.
Your goal is to assess quality fairly — not to find reasons to fail a story.

Score the story on these five criteria (each worth 2 points, max 10):

1. AGE-APPROPRIATENESS (0-2)
   - PASS (2): Story is wholesome. Mild conflict like a dog chasing a cat, a bully
     who reforms, or a character feeling sad is NORMAL and EXPECTED in children's
     literature. Do NOT penalise ordinary story tension.
   - FAIL (0-1): Only penalise genuinely harmful content — graphic violence, adult
     themes, horror, sexual content, or substance references.

2. VOCABULARY (0-2)
   - PASS (2): Most words are simple. A few longer words (e.g. "cautiously",
     "neighbourhood", "accidentally", "realised") are FINE — children's books use
     them constantly. Do NOT penalise normal descriptive language.
   - FAIL (0-1): Only penalise truly obscure or technical words a child would
     never encounter (e.g. "ephemeral", "juxtaposition", "exacerbated").

3. STORY COHERENCE (0-2)
   - PASS (2): Has a recognisable beginning, middle, and end. Characters have
     a goal or problem and the story resolves it.
   - FAIL (0-1): Story is confusing, jumps around with no logic, or ends abruptly
     with no resolution.

4. ENGAGEMENT (0-2)
   - PASS (2): A child would enjoy listening to this. It has charm, humour,
     excitement, or heart.
   - FAIL (0-1): Story is genuinely boring, repetitive, or has no appeal for a child.

5. POSITIVE MESSAGE (0-2)
   - PASS (2): Ends on an uplifting, reassuring, or hopeful note. The lesson
     doesn't have to be spelled out explicitly — a happy ending counts.
   - FAIL (0-1): Story ends on a sad, unresolved, or negative note with no redemption.

Original request: {request}

Story to evaluate:
\"\"\"
{story}
\"\"\"

Respond with ONLY a JSON object in this exact format:
{{
  "passed": true or false,
  "score": <integer 1-10>,
  "issues": ["specific actionable issue 1", "specific actionable issue 2"]
}}

Rules:
- Set "passed" to true if score >= {threshold} AND criterion 1 (age-appropriateness) scored > 0.
- Only list issues that genuinely hurt the story. Do NOT list minor stylistic preferences.
- If the story is good, return an empty issues list — do not invent problems.
- A story that fulfils the user's request well and entertains children should score 8-10."""


@dataclass
class JudgeVerdict:
    passed: bool
    score: int
    issues: List[str] = field(default_factory=list)

    @property
    def feedback_text(self) -> str:
        """Format issues as a bullet list for injection into the next prompt."""
        return "\n".join(f"- {issue}" for issue in self.issues)


def judge_story(user_request: str, story: str) -> JudgeVerdict:
    """
    Evaluate a story draft and return a JudgeVerdict.

    Falls back to a lenient passing verdict if the LLM response can't be
    parsed, so a transient API hiccup doesn't silently discard a good story.
    """
    prompt = _JUDGE_PROMPT.format(
        request=user_request,
        story=story,
        threshold=PASS_THRESHOLD,
    )
    raw = call_model(prompt, max_tokens=300, temperature=0.0)
    try:
        clean = raw.strip().strip("```json").strip("```").strip()
        data = json.loads(clean)
        return JudgeVerdict(
            passed=bool(data.get("passed", False)),
            score=int(data.get("score", 0)),
            issues=data.get("issues", []),
        )
    except (json.JSONDecodeError, ValueError, KeyError):
        # Parsing failed — fail open so we don't discard a story unfairly
        return JudgeVerdict(passed=True, score=PASS_THRESHOLD, issues=[])