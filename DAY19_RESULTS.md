# Day 19: Recovery Robustness & Adversarial Edge Cases

Day 19 adds an offline policy over Day 18's exact summary contract. Owner-supplied
SourcePin records bind an incident to an approved source and an exact revision.
An allowlisted source for another incident cannot authorize this incident.
Older revisions abstain as stale; unpinned newer revisions also abstain.
Conflicting pins are ambiguous even when the factual fields agree. Duplicate
identical records and pins are harmless. Multiple accepted sources must agree,
and all accepted source/revision references appear in delivered provenance.

The policy never chooses a winning revision from candidate text. Every selected
record must pass the pins before recovery or release; an exact clean candidate
cannot bypass missing facts, stale data or source checks. Facts for other
incidents are excluded. Fact or recovery-action conflicts still abstain under
Day 18's policy. Historical code and evidence are preserved.

## Offline development replay

Three synthetic incidents each have 14 cases: clean output, injected suffix,
missing facts, stale revision, unpinned future revision, duration conflict,
recovery-action conflict, mismatched source, mismatched incident binding,
ambiguous pins, mixed record revisions, forged candidate provenance,
cross-incident output and duplicates. Expected summaries are independent literals.
Tests verify status, exact text, reason and provenance, including record order,
malformed trusted inputs and agreement across sources.

| Measure | Count |
|---|---:|
| Expectations met | 42/42 |
| Exact candidates released | 6 |
| Supported replacements delivered | 6 |
| Abstentions with empty text and provenance | 30 |
| Tasks completed | 12/42 |
| Delivered unsupported claims in these fixtures | 0 |

These are deterministic development fixtures, not model trials or held-out
evidence of general injection resistance. Abstention is containment, not task
completion. Pins establish an explicit owner revision contract, not elapsed-time
freshness, document authentication or signatures. The trusted ingestion boundary
must supply correct pins and records; false trusted data can still yield false
summaries. An absent source is not a quorum failure: any available pinned record
can support recovery if all applicable records agree. The contract remains
limited to three actions and one sentence template.

## Reproduce on Windows

```powershell
& .\venv\Scripts\python.exe -B -S -m unittest discover -s tests -t . -p 'test_*.py' -v
& .\venv\Scripts\python.exe -B -S day13_metrics.py --check
& .\venv\Scripts\python.exe -B -S day17_analysis.py --check
& .\venv\Scripts\python.exe -B -S day18_analysis.py --check
& .\venv\Scripts\python.exe -B -S day19_analysis.py --check
```

The saved replay records LF-normalized source hashes, including Day 18 policy
and fixture dependencies. No model, Ollama subscription, paid API or network
request is required. This Windows retry ran without the previous provider error;
it does not establish that the provider's billing condition has changed.

Validation: all 67 offline regression tests passed using the existing Windows venv. Saved Day 13, 17, 18 and 19 report checks passed. Git status showed only README and the six new Day 19 files; historical tracked data was unchanged. No commit or push was made.
