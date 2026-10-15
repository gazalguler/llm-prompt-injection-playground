# Day 5: Testing the Output Validator

## Goal

I wanted to see how easily the output validator from Day 4 could miss different versions of the forbidden marker.

The original validator used a case-sensitive string comparison, so I tested whether changing letter case or using Unicode characters would affect its decision.

## Testing

I wrote eight local test cases using Python's unittest module.

Five cases used the forbidden marker or modified versions of it. Three were ordinary or incomplete strings that should remain allowed.

## Results

| Test | Expected | Actual |
|---|---|---|
| Exact marker | Block | Block |
| Lowercase | Block | Allow |
| Mixed case | Block | Allow |
| Fullwidth underscore | Block | Allow |
| Zero-width character | Block | Allow |
| Normal message | Allow | Allow |
| First word only | Allow | Allow |
| Second word only | Allow | Allow |

Four of the eight cases failed the new security requirements.

## What I Learned

Exact string matching works for a narrow rule, but it misses text that looks similar or has a different character representation.

These failures helped define the requirements for the improved validator in Day 6.

## Limitations

These were local unit tests, not new language model attacks. They demonstrate gaps in a string-matching rule rather than successful prompt injection against an LLM.

## Files

- `test_validator_day5.py`: original validator test cases
