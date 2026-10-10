# LLM Prompt Injection & Jailbreak Playground — Setup Guide (From Scratch)

This guide is written for someone who has never set up a Python project
before. Follow the steps in order.

## 1. Check that Python is installed

Open a terminal (Mac: Terminal, Windows: PowerShell) and type:

```
python3 --version
```

If you see `Python 3.10` or higher, you're set. If not, download and
install it from [python.org/downloads](https://www.python.org/downloads/).

## 2. Code editor

Use VS Code (if you don't have it, get it free from
[code.visualstudio.com](https://code.visualstudio.com/)). Open this folder
in VS Code.

## 3. Create a virtual environment

A virtual environment isolates this project's dependencies from other
projects on your machine. In the terminal, inside this folder:

```
python3 -m venv venv
```

Then activate it:

- Mac/Linux: `source venv/bin/activate`
- Windows: `venv\Scripts\activate`

If you see `(venv)` at the start of your terminal line, you're good.

## 4. Install dependencies

```
pip install -r requirements.txt
```

## 5. Get an OpenAI API key

1. Go to [platform.openai.com](https://platform.openai.com/) and create an account.
2. Go to the "API keys" section and create a new key.
3. Add a small amount of credit (5-10 USD) — `gpt-4o-mini` is very cheap,
   hundreds of test calls will cost only a few cents.

## 6. Create the `.env` file

Copy `.env.example`, rename it to `.env`, and paste your key inside:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

**Important:** never commit `.env` to GitHub (the `.gitignore` step below
takes care of this).

## 7. Run the script

```
python3 main.py
```

The script runs 20 tests across five categories and saves the responses to results.json, results.csv, and summary.md.

## 8. Push to GitHub

Make sure `.env`, `venv/`, and local backup files are excluded by `.gitignore`.

To create a local Git repository and commit the project:

```bash
git init
git branch -M main
git add .
git commit -m "Add prompt injection testing project"

```
## Next Steps

- Test different system prompts to see whether stronger instructions change the results.
- Improve the automatic evaluation to reduce false positives.
- Repeat experiments to check how consistent the responses are.
- Compare results across different models, including Claude and Gemini.
- Explore more realistic indirect prompt injection scenarios using untrusted documents.

## Initial Findings (October 2026)

I ran 20 prompts against gpt-4o-mini using the OpenAI API and reviewed each response manually.

Two prompts were normal baseline tests. Of the remaining 18 attack attempts, 16 failed to produce the forbidden phrase and two succeeded.

The two successful cases were both from the obfuscation category:

- Word combination: The model joined "OVERRIDE" and "SUCCESS" with an underscore and returned the forbidden phrase.
- Base64 decoding: The model decoded an encoded string and returned the same forbidden phrase.

Direct instruction overrides, role-play attempts, and prompts embedded in document-style text did not produce the forbidden phrase in this run.

One thing I found interesting was that the model refused direct requests to break the system instruction, but still produced the prohibited output when it was part of a simple text transformation task.

These results come from one run using one model and one system instruction. They are an initial observation, not a general measure of LLM security.

Results:
- results.json: Recorded model responses
- results.csv: CSV output
- results_reviewed.csv: Manually reviewed results
- results_week1.json: Original two-test experiment





