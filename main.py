import os
import openai
from agents import check_input, generate_story

"""
Before submitting the assignment, describe here in a few sentences what you would have built next if you spent 2 more hours on this project:

I would add the ability for the user to input their age such that the vocabulary and themes of the stories 
generated would match the age of the user.

I would have added streaming output so the story prints word-by-word for a more engaging experience,
and a "chapter continuation" feature letting the user say "keep going" to extend the story naturally.

I would also add a database that stores user information to give more personalized recommendations and
also have the ability to have recurring characters in stories.

Finally, I would spend more time going over all the prompts given to the agents as I've noticed that a lot of
times, a good prompt improves the performace of the pipeline significantly 

"""

def call_model(prompt: str, max_tokens=3000, temperature=0.1) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY") # please use your own openai api key here.
    openai.api_base = "https://openrouter.ai/api/v1"
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message["content"]  # type: ignore

example_requests = "A story about a girl named Alice and her best friend Bob, who happens to be a cat."


def main():
    user_input = input("What kind of story do you want to hear? ")

    safe, reason = check_input(user_input)
    if not safe:
        print(f"\n {reason}")
        return

    current_story, all_failed = generate_story(user_input)
    if all_failed:
        print("\n Couldn't generate a suitable story. Please try a different idea!")
        return

    print(f"\n{'='*60}\n{current_story}\n{'='*60}")

    while True:
        change = input("\nAny changes? (or press Enter to finish): ").strip()
        if not change:
            break

        safe, reason = check_input(change)
        if not safe:
            print(f"\n {reason}\n Keeping the current story.")
            continue

        new_story, all_failed = generate_story(f"{user_input}\n\nRevision: {change}")
        if not all_failed:
            current_story = new_story
        else:
            print(" Keeping the current story as-is.")

        print(f"\n{'='*60}\n{current_story}\n{'='*60}")

    print("\n Sweet dreams!")


if __name__ == "__main__":
    main()