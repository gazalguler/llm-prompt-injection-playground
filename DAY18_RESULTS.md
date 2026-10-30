# Day 18: Generalizing Recovery Across Multiple Incidents

Day 17 recovered blocked outputs for one fixed incident. Its Day 16 lexical
gate could still release a correct summary with an unsupported claim appended.
Day 18 uses an exact output contract tied to the requested incident's trusted
records, including when deciding whether to preserve a candidate.

## Trusted facts and provenance

The new fixtures cover a 15-minute database restart, a 42-minute queue
configuration rollback and a 7-minute cache failover. Each record contains an
incident ID, owner source ID, revision, duration and recovery action. Every
delivered summary carries the source/revision references used to construct it.
These are synthetic owner fixtures, not facts extracted from model responses.

The caller supplies both records and source approvals through a trusted path.
Source names are references, not authentication: copying a source name into a
retrieved document must never grant trust. The code does not fetch documents,
verify signatures or authenticate a caller. Production use needs that boundary.

Only records for the requested incident participate. Missing records, invalid
fields, unapproved sources and disagreements about either fact cause abstention,
even if the candidate looks correct. A newer revision never silently overrides
a conflict. Agreeing records retain all distinct source/revision references.

## Offline results

Each incident has one clean control and seven probes. Probes include a different
incident's summary, an unsupported extra claim, forged authority, a redirect,
missing facts, conflicting facts and an unapproved source. Expected summaries
are written independently of the renderer. Regression tests add malformed types,
conflicting recovery actions, record ordering and absent trusted inputs.

| Measure | Count |
|---|---:|
| Development cases matching expectations | 24/24 |
| Original candidates contained | 21/24 |
| Exact clean candidates released | 3/3 |
| Candidates recovered from trusted facts | 12 |
| Abstentions, with no delivered text | 9 |
| Final tasks completed | 15/24 |
| Delivered unsupported factual claims | 0/24 |

Containment means the original candidate was withheld; it includes recovery and
abstention. Recovery means a supported replacement was delivered. Completion
requires a delivered summary matching the independent expected incident facts.
Abstentions are not counted as completed tasks. The zero unsupported-claim count
applies to these fixtures only, not a measured real-world factuality rate.

## Reproduce

No packages, credentials or API requests are needed:

```sh
python -B -S -m unittest discover -s tests -t . -p 'test_*.py' -v
python -B -S day13_metrics.py --check
python -B -S day17_analysis.py --check
python -B -S day18_analysis.py --check
```

The saved Day 18 replay includes LF-normalized hashes of its fixture, recovery
and analysis sources. Tests compare reports under simulated LF and CRLF source
reads. Historical data and Day 16/17 behavior remain unchanged.

Validation passed all 63 offline tests in both LF and CRLF file copies on
Windows, along with the Day 13, 17 and 18 report checks. This checks checkout
line-ending reproducibility; Linux execution has not been run locally.
The tracked and proposed files passed a secret-pattern scan, `.env` stayed
excluded, and historical run files retained their byte hashes. No live API
calls were made.

## Limits

This is a deterministic renderer and conservative release policy, not a model
evaluation or general factuality verifier. It supports three recovery actions
and one sentence template. Correct paraphrases are replaced, which costs output
diversity. Trusted but incorrect records can still produce incorrect summaries.
These development fixtures demonstrate isolation and abstention behavior; they
are not held-out evidence of general prompt injection resistance.
