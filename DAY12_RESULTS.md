# Day 12: Offline Security Regression Tests

## Scope

Nine deterministic unittest tests cover the Day 11 mock retrieval and tool-message
workflow. They run without third-party packages, API keys, or model requests.

- Retrieval: all three known IDs, document schema, factual anchors, unknown IDs,
  and attack-marker separation between the malicious document and clean controls.
- Messages: system/user/assistant/tool ordering, exact trusted instructions,
  function name and JSON arguments, and matching tool-call/result IDs.
- Isolation: all five attack payloads remain inside serialized tool content;
  trusted messages and source documents stay unchanged. Repeated calls are independent.
- Dataset: exact attack IDs, unique payloads, factual anchors and attack marker.
- Records: complete case/condition coverage without duplicates; raw JSON/CSV
  agreement; manual reviews preserve raw fields; marker flags agree with responses.
- Reviews: six initial records (two resisted, four not applicable); ten expanded
  records (baseline: two success, three resisted; trust boundary: five resisted).
  Task completion is checked separately from attack success.

The live attack evaluator now uses `build_attack_messages`, a pure helper shared
with the offline tests. This preserves the existing API message sequence and makes
the actual attack-message construction testable without importing the API client.

## Validation

```bash
python -S -m unittest discover -s tests -t . -p 'test_*.py' -v
```

Result: **19 tests passed**, including nine Day 12 tests and ten existing tests.
The `-S` flag disables site packages. CI uses the same offline command and does
not install the OpenAI SDK or load `.env`. No live API experiments were run.

## Live evaluation and limits

`day11_evaluate.py` and `day11_attack_evaluate.py` remain explicit live commands
outside CI discovery. They require dependencies and credentials, incur API costs,
and overwrite raw result files; use a separate checkout to retain these fixtures.

Passing these tests establishes message structure and consistency of the saved
historical results. It does not establish that a model will ignore malicious tool
content. Prompt wording and structural isolation alone are not a security guarantee.
The manual review counts describe the small Day 11 dataset, not general attack rates.
