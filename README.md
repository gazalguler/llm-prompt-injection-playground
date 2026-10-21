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

## Day 3: Evaluation on New Attack Examples

I tested both the original and hardened system prompts against 10 new attack examples using the OpenAI API.

| Metric | Original | Hardened |
|---|---:|---:|
| Attack attempts | 10 | 10 |
| Successful attacks | 2 | 2 |
| Attack success rate | 20% | 20% |

The hardened prompt still produced the forbidden marker in two string-construction tests, sometimes while stating that it could not provide that output.

I also found errors in the original automated evaluator. After correcting the exact-marker detection, the automated labels matched all 20 manually reviewed results.

These findings are limited to this small test set and do not establish general security performance.

Read the full report: [Day 3 Results](DAY3_RESULTS.md).
## Day 4: Output Validation

I added a Python output validator to test whether application-level filtering can prevent forbidden content from reaching the user.

Using 20 previously recorded API responses from Day 3:

| Metric | Original + Validator | Hardened + Validator |
|---|---:|---:|
| Raw violations | 2/10 | 2/10 |
| Blocked responses | 2/10 | 2/10 |
| Delivered violations | 0/10 | 0/10 |

The validator also passed 10 local unit tests.

The model still generated the forbidden marker, but the validator blocked those recorded responses before delivery.

This is an exact-match demonstration, not a general prompt injection defense.

Full report: [Day 4 Results](DAY4_RESULTS.md).
## Day 5: Validator Bypass Testing

I tested the original output validator against eight local examples. Four failed the updated detection requirements, including lowercase text, mixed case, a fullwidth underscore, and a zero-width character.

These were local string-matching tests, not new LLM API attacks.

Full results: [Day 5 Results](DAY5_RESULTS.md).

## Day 6: Improved Output Validator

I built a second validator using Unicode normalization and case-insensitive matching.

- Initial 8 tests: original 4/8, improved 8/8
- Additional 14 tests: original 9/14, improved 14/14
- Total local scenarios: original 13/22, improved 22/22
- Recorded API responses: both validators blocked 4/20

The improved version detected more text variants in local tests, although both versions made the same decisions on the 20 recorded responses.

Full results: [Day 6 Results](DAY6_RESULTS.md).
## Day 7: Automated Testing

I reorganized the validator tests into a shared test suite and removed duplicate cases.

Both validators now run against the same 17 unique test scenarios:

| Validator | Passed | Failed |
|---|---:|---:|
| Original | 11 | 6 |
| Improved | 17 | 0 |

I also added a GitHub Actions workflow to run the improved validator tests on pushes and pull requests.

The original validator is kept as a baseline for comparison. Its known limitations do not cause the CI workflow to fail.

Run the tests locally:

```bash
python -m unittest -v tests.test_validators

```

These are local tests of a specific output-filtering rule, not a measure of general prompt injection resistance.
## Day 8: CI Maintenance and Edge-Case Testing

I updated the GitHub Actions workflow and added 10 edge-case tests to explore how the validator handles character variations and ordinary responses.

The test suite now uses automatic discovery, so new test files can be included without changing the workflow.

- 17 shared validator scenarios
- 10 additional edge-case scenarios
- 27/27 scenarios matched the expected behavior
- No new OpenAI API calls

Some text variants are still allowed under the current policy. Passing the tests does not mean the validator can prevent all prompt injection attacks.

Full report: [Day 8 Results](DAY8_RESULTS.md).
## Day 9: Security Policy and Normalization

I revisited the validator's detection rules after noticing that newline and tab characters could split the forbidden marker without triggering a block.

I updated the normalization logic and revised the earlier tests to match the new security policy.

- Four previously missed marker variants are now blocked.
- Five ordinary responses passed the policy tests.
- Four additional tests examined multiline text and normalization tradeoffs.
- The full regression suite passed locally.

The change improves detection for these specific variants, but joining characters across lines can also cause unnecessary blocking. I haven't measured a real-world false-positive rate.

Full report: [Day 9 Results](DAY9_RESULTS.md).
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
