"""
pipeline.py — Orchestrates the full story generation pipeline.

Flow:
  guardrails check → classify genre → [generate → judge → retry loop]

If all retries fail AND every score is below PASS_THRESHOLD, the pipeline
signals the caller to fall back to the previous story rather than surfacing
a bad result.
"""

from dataclasses import dataclass
from typing import Optional

from config import MAX_RETRIES, PASS_THRESHOLD
from classifier import classify_genre
from prompt_builder import build_story_prompt
from judge import judge_story, JudgeVerdict
from llm_client import call_model


@dataclass
class PipelineResult:
    story: str
    score: int
    passed: bool
    all_failed: bool   # True when every attempt scored below PASS_THRESHOLD


def generate_story(user_request: str, verbose: bool = True) -> PipelineResult:
    """
    Run the full generation pipeline for a given request.

    Returns a PipelineResult. The caller is responsible for deciding what to
    do when all_failed=True (e.g. display the previous story instead).
    """
    genre = classify_genre(user_request)
    if verbose:
        print(f"\n📚 Genre detected: {genre}")

    feedback = ""
    best_story = ""
    best_score = 0
    any_passed = False

    for attempt in range(1, MAX_RETRIES + 1):
        if verbose:
            print(f"✍️  Generating draft {attempt}/{MAX_RETRIES}...")

        prompt = build_story_prompt(user_request, genre, feedback)
        story = call_model(prompt, max_tokens=700, temperature=0.75)

        if verbose:
            print("🔍 Judging draft...")

        verdict: JudgeVerdict = judge_story(user_request, story)

        if verbose:
            status = "✅ PASSED" if verdict.passed else "❌ FAILED"
            print(f"   {status} | Score: {verdict.score}/10")
            for issue in verdict.issues:
                print(f"   • {issue}")

        # Track best draft regardless of pass/fail
        if verdict.score > best_score:
            best_score = verdict.score
            best_story = story

        if verdict.passed:
            any_passed = True
            if verbose:
                print()
            return PipelineResult(
                story=story,
                score=verdict.score,
                passed=True,
                all_failed=False,
            )

        # Prepare feedback for next iteration
        feedback = verdict.feedback_text

    # All retries exhausted
    all_failed = best_score < PASS_THRESHOLD

    if verbose:
        if all_failed:
            print(
                f"\n⛔ All {MAX_RETRIES} drafts scored below the threshold "
                f"({best_score}/10 < {PASS_THRESHOLD}/10). "
                f"Reverting to the previous story.\n"
            )
        else:
            print(
                f"\n⚠️  Max retries reached. "
                f"Best draft score: {best_score}/10\n"
            )

    return PipelineResult(
        story=best_story,
        score=best_score,
        passed=False,
        all_failed=all_failed,
    )
