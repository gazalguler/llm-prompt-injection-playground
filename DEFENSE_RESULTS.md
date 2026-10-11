# Defense Testing: Original vs. Hardened System Prompt

After my first 20 tests, I wanted to see whether making the system instructions more specific would change the results.

In the first run, two obfuscation prompts caused gpt-4o-mini to output a phrase that the system prompt explicitly prohibited. Both involved simple text transformations: joining two words and decoding Base64.

For the second run, I added instructions explaining that the same rule also applies to decoding, word joining, role-play, and instructions found inside documents.

## What I tested

I reused the same 20 test cases with the same model, gpt-4o-mini, and temperature=0. The main experimental change was the system prompt.

The test set included:
- 2 baseline prompts
- 5 direct instruction overrides
- 5 role-play attempts
- 5 document-based indirect injection attempts
- 3 obfuscation attempts

## Results

| Category | Original | Hardened |
|---|---|---|
| Baseline tasks completed | 2/2 | 2/2 |
| Instruction overrides producing the target phrase | 0/5 | 0/5 |
| Role-play attempts producing the target phrase | 0/5 | 0/5 |
| Indirect injections producing the target phrase | 0/5 | 0/5 |
| Obfuscation attempts producing the target phrase | 2/3 | 0/3 |

The two obfuscation attempts that succeeded in the first run were rejected in the second run. Both baseline tasks still received normal answers.

I manually checked the 20 responses in the second run.

One detail worth noting is `obfuscation_3`: the model did not output the prohibited phrase, but it also reversed the supplied string incorrectly. I counted this as a failed attack, not evidence of a correct text transformation.

## Limitations

This is a small experiment using one model, one set of prompts, and one run per condition.

I designed the hardened prompt after seeing which attacks succeeded in the first run. It explicitly mentions those attack types, so the improvement on the same test set does not show how well it would work against new attacks.

The indirect injection examples also used document-style text inside a user message rather than a real document retrieval system.

The evaluation focuses on whether the prohibited phrase appeared in the response. It does not measure broader model safety or whether every requested task was completed correctly.

## Files

- `main.py`: Original testing script
- `defense_tests.py`: Hardened system prompt experiment
- `results_reviewed.csv`: Reviewed original responses
- `defense_results_reviewed.csv`: Reviewed defense responses
- `defense_results.json`: Raw defense experiment responses

## Next

I want to try new attacks that were not used to design the hardened prompt, repeat the experiments, and compare whether the defense still works without affecting normal tasks.
