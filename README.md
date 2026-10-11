# LLM Prompt Injection & Jailbreak Playground

I started this project to learn more about prompt injection and jailbreak attacks, and to see how LLMs respond when someone tries to make them ignore their instructions.

I began with a simple Python script using the OpenAI API. The first version had just two tests, but I've since expanded it to 20 prompts across five categories. I'm using the results to understand which approaches work, which don't, and why.

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
- results_reviewed.csv: A saved copy with manual reviews for all 20 tests. I kept this separate because running the script again overwrites results.csv.
- results_week1.json: Original two-test experiment

## Defense Testing

I also tested a stronger system prompt against the same 20 prompts. In this run, neither of the two previously successful obfuscation attacks produced the prohibited phrase, and both baseline tasks still worked.

I documented the comparison, results, and limitations in [DEFENSE_RESULTS.md](DEFENSE_RESULTS.md).
## Setup

You'll need Python 3.10+ and an OpenAI API key.

### 1. Install dependencies

```bash
python -m venv venv
```

Activate the environment:

- Windows PowerShell: `.\venv\Scripts\Activate.ps1`
- Mac/Linux: `source venv/bin/activate`

Then install the packages:

```bash
pip install -r requirements.txt
```

### 2. Add your API key

Copy `.env.example` to a new file called `.env` and add your OpenAI API key.

The `.gitignore` file keeps `.env` out of Git. Never commit your API key.

### 3. Run the tests

```bash
python main.py
```

The script runs 20 test cases and saves the responses to `results.json`, `results.csv`, and `summary.md`.

Running the tests uses the OpenAI API and may incur charges.

## Next Steps

- Test different system prompts to see whether stronger instructions change the results.
- Improve the automatic evaluation to reduce false positives.
- Repeat experiments to check how consistent the responses are.
- Compare results across different models, including Claude and Gemini.
- Explore more realistic indirect prompt injection scenarios using untrusted documents.





