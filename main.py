"""
main.py — Entry point for the Bedtime Story Generator.

Before submitting the assignment, describe here in a few sentences what you
would have built next if you spent 2 more hours on this project:

I would have added a streaming output mode so the story prints word-by-word
for a more engaging reading experience, and a simple "chapter continuation"
feature that lets the user say "keep going" to extend the story naturally.
I'd also have refined the judge rubric to score on a per-sentence vocabulary
level (using a Flesch-Kincaid approximation) so the feedback is more precise
and the rewrites converge faster.
"""

from guardrails import check_input
from pipeline import generate_story

DIVIDER = "─" * 60
STORY_BORDER = "=" * 60


def print_story(story: str) -> None:
    print(f"\n{STORY_BORDER}")
    print(story)
    print(STORY_BORDER)


def revision_loop(original_request: str, current_story: str) -> None:
    """
    After the initial story is shown, repeatedly prompt the user for changes.

    Guardrails are applied to every revision request. If a revision causes
    all generation attempts to fail (all_failed=True), the current story is
    kept and the user is told why.
    """
    while True:
        print(f"\n{DIVIDER}")
        change = input(
            "Any changes? (e.g. 'make it funnier', or press Enter to finish): "
        ).strip()

        if not change:
            break

        # ── Guardrails check on the revision request ──────────────────────────
        guard = check_input(change)
        if not guard.safe:
            print(f"\n {guard.reason}")
            print("The original story has been kept.\n")
            continue

        # ── Run the pipeline with the revision folded in ──────────────────────
        revision_request = f"{original_request}\n\nRevision request: {change}"
        result = generate_story(revision_request, verbose=True)

        if result.all_failed:
            # Every draft scored below threshold — keep the current story
            print("📖 Keeping the current story as-is.")
            print_story(current_story)
        else:
            # Accept the new story (even if it didn't formally pass, it's
            # the best we could do and it's above the threshold)
            current_story = result.story
            print_story(current_story)


def main() -> None:
    print(" Welcome to the Bedtime Story Generator!")
    print(DIVIDER)
    user_input = input("What kind of story do you want to hear? ").strip()

    if not user_input:
        user_input = (
            "A story about a girl named Alice and her best friend Bob, "
            "who happens to be a cat."
        )
        print(f"(Using example request: {user_input})")

    # ── Guardrails check on the initial request ───────────────────────────────
    guard = check_input(user_input)
    if not guard.safe:
        print(f"\n {guard.reason}")
        print("Please restart and try a different story idea. Sweet dreams! 🌟")
        return

    # ── Generate the initial story ────────────────────────────────────────────
    result = generate_story(user_input, verbose=True)

    if result.all_failed:
        print(
            "\n Sorry, we couldn't generate a suitable story for that request. "
            "Please try a different idea!"
        )
        return

    print_story(result.story)

    # ── Revision loop (with guardrails + fallback logic built in) ────────────
    revision_loop(user_input, result.story)

    print("\n Sweet dreams!")


if __name__ == "__main__":
    main()
