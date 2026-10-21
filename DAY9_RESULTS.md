# Day 9: Security Policy and Normalization

## Goal

I wanted to check whether the validator's existing behavior matched the security rules I actually wanted to enforce.

Some tests from Day 8 allowed markers split across lines or tabs. That matched the implementation at the time, but it left a gap in the detection policy.

## Changes

I updated the normalization function to ignore newline, carriage return, and tab characters when checking for the forbidden marker.

The original response is still preserved when validation allows it.

I also updated the earlier edge-case expectations to reflect the new policy.

## Results

Four new security cases failed before the change and passed afterward:

- Newline inside the marker
- Tab inside the marker
- Newline before the underscore
- Tab after the underscore

Five ordinary responses passed the initial policy tests.

I added four more tests to examine normalization behavior, including ordinary multiline content and text split across separate lines. All four passed.

The complete test suite passed after these changes.

## Tradeoffs

Removing line breaks during validation can detect some attempts to split a forbidden string.

However, it can also join text that was intended to remain separate. An innocent document could be blocked if characters on adjacent lines happen to form the marker.

This is a tradeoff in the detection policy, not evidence of a measured false-positive rate.

## Limitations

- The policy still checks for one specific forbidden marker.
- Some Unicode lookalikes and combining-character variations are not detected.
- The examples were manually selected.
- No new LLM API requests were made.
- This is output filtering, not a complete defense against prompt injection.

## Files

- `improved_validator.py`: updated normalization
- `tests/test_security_policy.py`: security policy tests
- `tests/test_edge_cases.py`: updated expectations
- `tests/test_normalization_tradeoffs.py`: normalization tradeoff tests
