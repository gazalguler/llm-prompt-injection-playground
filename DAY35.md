# Day 35 — Seeded Randomized State Transitions

November 20, 2026 (America/Vancouver)

Day 34 varied delivery faults on a fixed schedule. Day 35 also varies when
workers act and which operations they try. Each trace starts with fresh
sender and receiver SQLite files and uses the same independent in-memory
model as Day 34 to predict the results.

## Method

Python's `random.Random` uses the 64 published seeds from 3500 through
3563. The run produced traces of 21–54 actions, for 2,518 actions total.
Each action checks the persisted outbox, receipt and effect rows against
the model, including after restarts. That is 7,554 table comparisons,
plus 192 for initial state. Operations that return a result are also
checked against the model. Fresh lease tokens must differ from all
previous tokens in that trace and match the persisted claim.

The random steps sample times around acceptance, lease expiry and grant
expiry. They mix enqueue, claim, acknowledge, delivery, authorization
changes, direct receiver calls and restarts. Some traces start with
short directed sequences so the suite reaches cases that random steps
may miss. Those openings check exhaustion, recovery after a lost
acknowledgement, and delivery after rejecting frames with a changed
recipient or payload.

A revoked or revised grant cannot reclaim the original intent. An old
or invalid token cannot acknowledge the active lease, and a completed
row stays completed. The receiver rejects the wrong recipient and
rejects a changed payload for an existing receipt. Identical retries
reuse the receipt and leave one committed effect for that operation.
The recovery sequence restores the original authority and finishes
while another claim is still available. The exhaustion sequence shows
that a healthy transport cannot revive an expired final claim.

## Replay

Run the complete seed set or select one seed from the repository root
with Python 3.13. A failing subtest includes its seed, action number
and the actions through the point of failure.

```sh
python -m unittest tests.test_day35_randomized_recovery
DAY35_SEED=3501 python -m unittest tests.test_day35_randomized_recovery
```

## Results and limits

Unittest and pytest ran the same 253 unique test methods. Both reported
248 passed, five skipped and zero failed. Pytest also reported 779 passing
subtests, 64 of them from Day 35. The five skips require the private Day 23
archive. The standalone sealed review also requires that archive. The
historical metrics and offline replays, five public package verifiers and
publication privacy scan passed.

Each trace covers one operation with a five-second lease, a three-claim
budget and a retained receiver database. Time and caller identity are
supplied by the test. Reopening uses fresh worker instances in the same
process. The traces exercise local SQLite effects and provide no guarantee
about remote delivery, production exactly-once behavior or eventual
completion outside the recovery conditions covered here. The run used no
model, Ollama, OpenAI or paid API calls.
