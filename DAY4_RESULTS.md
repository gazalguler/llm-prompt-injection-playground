# Day 4: Output Validation and Defense in Depth

## Research Question

Can an application-level output validator prevent a forbidden marker from reaching the user when the language model fails to follow its system prompt?

## Method

I implemented a Python output validator that checks model responses for the exact string `OVERRIDE_SUCCESS`.

If the marker appears anywhere in a response, the validator replaces the entire response with a fixed blocking message.

Otherwise, the original response is returned unchanged.

I evaluated the validator using 20 previously recorded API responses from Day 3:

- 10 responses from the original system prompt
- 10 responses from the hardened system prompt

No additional API calls were made for this evaluation.

## Results

| Metric | Original + Validator | Hardened + Validator |
|---|---:|---:|
| Recorded responses | 10 | 10 |
| Raw model violations | 2 | 2 |
| Responses blocked | 2 | 2 |
| Delivered violations | 0 | 0 |

The validator blocked all four recorded responses containing the exact forbidden marker.

This does not mean the underlying model stopped producing the marker. The application-level control prevented those responses from being delivered.

## Unit Tests

I also ran 10 local test cases covering:

- Ordinary responses
- Mathematical and programming explanations
- Security advice and summaries
- Lowercase and altered marker variants
- Exact marker matches
- Markers embedded in sentences and refusals

All 10 tests produced the expected results under the implemented exact-match policy.

These are unit test results, not a measured false-positive rate on real user traffic.

## Key Findings

### 1. Output validation adds an independent defense layer

The system prompt alone did not prevent all violations in Day 3.

The Python validator blocked those recorded violations before delivery.

### 2. Refusal language does not guarantee compliance

Some model responses included the forbidden marker while simultaneously stating they could not provide it.

The validator checked the actual response content rather than relying on the model's explanation.

### 3. The validator has a narrow scope

The current implementation only detects the exact, case-sensitive string `OVERRIDE_SUCCESS`.

It does not block lowercase versions, encoded variants, or semantically equivalent content.

### 4. Output blocking can reduce usefulness

An entire response is replaced when the marker appears, even if the rest of the response contains useful information.

Further testing is needed to study legitimate task completion and unnecessary blocking.

## Limitations

- The evaluation reused existing responses instead of making new API calls.
- The test covered only one forbidden marker.
- The validator uses exact string matching.
- The demonstration does not include a live application or streaming-output integration.
- The 10 unit tests were manually created.
- No representative false-positive rate was measured.
- Output filtering alone does not address data exfiltration, unsafe tool calls, or other prompt injection outcomes.

The results demonstrate a narrowly defined application-level control, not general protection against prompt injection.

## Next Steps

- Evaluate case-insensitive and normalized matching.
- Add more systematic unit tests.
- Test the impact of output filtering on legitimate tasks.
- Explore input isolation and tool-permission controls.

## Files

- `output_validator.py`: exact-match output validator
- `day4_evaluate.py`: evaluation using recorded API responses
- `day4_results.json`: recorded evaluation results
- `day4_results.csv`: CSV evaluation results
- `day4_validator_tests.py`: local validator tests
