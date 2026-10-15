# Day 6: Improving the Output Validator

## Goal

After finding several gaps in the original validator, I built a second version that handles common text variations without adding external dependencies.

I kept the original implementation so I could compare both versions.

## Implementation

The improved validator uses three steps:

1. Apply Unicode NFKC normalization.
2. Remove Unicode formatting characters (category Cf).
3. Use casefold() for case-insensitive comparison.

The validator checks the normalized response for the normalized forbidden marker.

If a match is found, it replaces the entire response with a fixed blocking message. Otherwise, it returns the original response unchanged.

## Local Tests

I ran the eight Day 5 scenarios against both validators.

| Result | Original | Improved |
|---|---:|---:|
| Passed | 4 | 8 |
| Failed | 4 | 0 |

I also tested the improved validator with 14 additional cases:

- 6 cases expected to be blocked
- 8 cases expected to be allowed

All 14 produced the expected decisions.

## Recorded API Response Comparison

I applied both validators to 20 responses saved during Day 3. This was an offline evaluation, so no new API calls were made.

| Metric | Original | Improved |
|---|---:|---:|
| Recorded responses | 20 | 20 |
| Blocked | 4 | 4 |
| Allowed | 16 | 16 |

There were no differences between the validators on these recorded responses.

The additional detection capability was demonstrated by local variant tests, not by new live attacks.

## Limitations

- Unicode normalization does not handle every possible encoding or text transformation.
- Removing formatting characters could change the meaning of some legitimate text.
- The validator still checks for one specific marker.
- A match anywhere in the response causes the entire response to be blocked.
- The test cases were manually selected and do not establish a real-world false-positive rate.
- The improved validator has not been integrated into a streaming or tool-using application.

## Next Steps

I want to expand the test coverage, check for unnecessary blocking, and explore how output validation could work alongside stronger input handling and tool-permission controls.

## Files

- `improved_validator.py`: Unicode-aware output validator
- `test_validator_day6.py`: original eight tests applied to the improved validator
- `test_validator_extended.py`: additional local tests
- `day6_compare.py`: offline comparison using Day 3 responses
- `day6_comparison.csv`: comparison results
