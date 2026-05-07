# Bedtime Story Generator

A multi-agent LLM pipeline that turns any story request into a child-safe,
age-appropriate bedtime story for ages 5–10.

## File Structure

```
story_generator/
├── main.py           # Entry point — user I/O and revision loop
├── config.py         # Constants: model, thresholds, genres, guidance
├── llm_client.py     # Thin OpenAI/OpenRouter API wrapper (call_model)
├── guardrails.py     # Safety agent — screens requests before generation
├── classifier.py     # Genre classifier agent
├── prompt_builder.py # Assembles the storyteller prompt
├── judge.py          # LLM judge agent — scores and critiques drafts
└── pipeline.py       # Orchestrates classify → generate → judge → retry
```

## Setup

1. Install dependencies:
   ```bash
   pip install openai
   ```

2. Set your API key (OpenRouter recommended — free tier available):
   ```bash
   export OPENROUTER_API_KEY=sk-or-...
   ```
   To use OpenAI directly instead, set `API_BASE = None` in `config.py`
   and set `OPENAI_API_KEY` instead.

3. Run:
   ```bash
   python main.py
   ```

## How It Works

```
User request
    │
    ▼
Guardrails agent ──[unsafe]──▶ Block + explain
    │ safe
    ▼
Genre classifier  ──────────▶ adventure / bedtime / silly / mystery / friendship
    │
    ▼
Prompt builder    ──────────▶ Injects genre tips + age rules + 3-act arc
    │
    ▼
Storyteller LLM   ──────────▶ Generates draft
    │
    ▼
LLM Judge         ──────────▶ Scores 1-10, lists issues
    │
    ├── score ≥ 7 ──────────▶ Accept & print story
    │
    └── score < 7 ──────────▶ Retry with feedback (max 3 attempts)
                                  │
                                  └── all failed below threshold ──▶ Keep previous story
```

## Guardrails

Two-layer safety check runs on every request and every revision:
- **Layer 1 (fast):** Regex keyword scan — instant, no API call.
- **Layer 2 (deep):** LLM semantic check — catches subtle or reworded requests.

If a revision request fails guardrails, or if all generation attempts score
below the threshold, the previously accepted story is preserved.

## Configuration (config.py)

| Setting | Default | Description |
|---|---|---|
| `MAX_RETRIES` | 3 | Max judge → rewrite cycles |
| `PASS_THRESHOLD` | 7 | Minimum score (out of 10) to accept a story |
| `MODEL` | gpt-3.5-turbo | LLM model to use |
| `API_BASE` | OpenRouter URL | Set to `None` for direct OpenAI |
