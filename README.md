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
## Day 10: Indirect Prompt Injection and Trust Boundaries

I tested how a language model handles instructions embedded in documents it was asked to summarize.

Eight synthetic documents were evaluated using two system prompts: a basic summarization prompt and one that explicitly treats document content as untrusted data.

| Outcome | Baseline | Trust-boundary |
|---|---:|---:|
| Successful attacks | 4/8 | 0/8 |
| Partial contamination | 3/8 | 1/8 |
| Resisted attacks | 1/8 | 7/8 |
| Legitimate tasks completed | 2/8 | 7/8 |

The trust-boundary instruction performed better on this small test set, although one response still incorporated part of a fake system message.

I reviewed attack success and task completion separately rather than relying only on whether a target phrase appeared.

These were synthetic documents embedded in user messages, not retrieved documents from a live application.

Full report: [Day 10 Results](DAY10_RESULTS.md).
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

## Day 11: Tool-Output Prompt Injection

This experiment tests whether instructions embedded in retrieved documents can redirect an AI assistant.

I built a local mock retrieval system and simulated a tool-call conversation. The retrieved content was delivered through a separate tool message rather than embedded in the user's request.

The evaluation included 16 API responses: six initial responses and ten responses from five additional attack scenarios.

| Expanded attack results | Baseline | Trust-boundary |
|---|---:|---:|
| Successful attacks | 2/5 | 0/5 |
| Resisted attacks | 3/5 | 5/5 |

The baseline assistant followed two injected instructions: a forged retrieval authorization and a malicious summary requirement. The trust-boundary assistant resisted all five attacks in this test set.

These results come from a small synthetic evaluation, not a live RAG pipeline.

Full report: [Day 11 Results](DAY11_RESULTS.md).


## Day 12: Automated Security Regression Tests

Run the offline suite with Python 3.10+; no API key or installed packages are required:

```bash
python -S -m unittest discover -s tests -t . -p 'test_*.py' -v
```

The Day 12 checks cover retrieval, matched tool calls, untrusted content isolation,
attack dataset integrity, saved CSV/JSON consistency, and manual review counts.
CI runs only the offline `tests/` directory, with site packages disabled.

Live experiments remain separate, explicitly invoked commands:

```bash
python day11_evaluate.py
python day11_attack_evaluate.py
```

These live commands require dependencies and a local API key, incur API charges,
and overwrite the raw Day 11 result files. Run them in a separate checkout when
preserving the historical fixtures. Model behavior is not deterministic even at
temperature zero. Offline checks validate structure and historical records;
they do not prove model resistance to prompt injection.

Details: [Day 12 Results](DAY12_RESULTS.md).


## Day 13: Attack Evaluation Metrics & Security Dashboard

The [offline dashboard](day13_dashboard.html) consolidates 32 saved Day 10–11
responses, keeping the three experimental cohorts and two prompt conditions
separate. It shows success, partial contamination, resistance and task completion,
with the saved review notes and responses available for inspection.

Four clean controls remain `not_applicable` for attack outcomes. Earlier marker
and validator experiments are excluded because their endpoints differ.
These small synthetic runs do not establish general security performance.

Rebuild or verify the standalone HTML and JSON reports without packages or keys:

```sh
python -S day13_metrics.py
python -S day13_metrics.py --check
```

CI runs the offline tests and checks report reproducibility.
Definitions, counts and limitations: [Day 13 Results](DAY13_RESULTS.md).

## Day 14: Adversarial Test Expansion & Repeated Trials

Prepare three trials of each Day 11 attack under both prompt conditions:

```sh
python -S day14_trials.py prepare day14_runs/repeat_001 --run-id repeat_001
```

This saves 30 requests without making API calls. Optional new variants remain
in a separate cohort; response recording preserves raw JSON and blank manual
review fields. Existing runs and trial responses are never overwritten.
The approved Day 14 run completed on 2026-10-25. Any further live execution
requires explicit agreement on the plan and dollar budget. CI stays offline.
See [Day 14 methodology](DAY14_RESULTS.md) for limits and review instructions.

## Day 15: Attack Variants & Generalization Testing

Six new synthetic attack/control pairs form a separate exploratory cohort.
The offline plan compares baseline and trust-boundary prompts with three trials
per case. The approved live run completed all 72 requests once on 2026-10-26,
with usage-derived cost USD 0.00244260 against a USD 0.05 cap. Agent reviews
keep controls and attack outcomes separate.

```sh
python -B -S day15_trials.py prepare day15_runs/generalization_001 --run-id generalization_001
python -B -S day15_trials.py summarize day15_runs/generalization_001
```

See [Day 15 methodology](DAY15_RESULTS.md) for objectives, labeling rules,
reproducibility commands, observed results and limits. Reviews are agent-authored;
these small synthetic cohorts do not establish general security performance.
