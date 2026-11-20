# Day 34 — Recovery State Machine & Model-Based Testing

November 19, 2026 (America/Vancouver)

Day 34 checks the Day 30 SQLite outbox, Day 31 receiver, and Day 32 delivery
adapter together. Day 33 tests selected process exits around commits. These
tests check how the committed state evolves over bounded sequences of delivery
attempts and fresh worker instances.

## Reference model

The in-memory model predicts outcomes from the operation history and supplied
clock. It reads no database rows and calls no delivery or authorization code.
It models one operation with a five-second outbox lease and a budget of three
successful claims. The authorization inputs are the original synthetic grant,
its revocation, and a valid grant for a changed record revision and rendered
payload.

| State or condition | Expected behavior |
| --- | --- |
| Absent | A valid enqueue writes the original intent as pending with zero attempts. A delivery attempt cannot claim an absent row. |
| Pending | A valid claim starts the first lease. Re-enqueuing the original intent preserves its acceptance time. A claim dated before acceptance fails. |
| Leased | A claim increments the attempt count and assigns a fresh token. An acknowledgement needs the current token and a time from lease start up to, but excluding, its deadline. |
| Expired lease | The row still says `leased`. At the deadline an authorized worker can reclaim it if the retry budget permits. Reclaiming fences out the previous token. |
| Exhausted budget | The row retains its final lease and attempt count. Once that lease expires, a healthy transport still cannot deliver the operation. |
| Done | Acknowledgement records completion. Further claims and acknowledgements fail. The row retains the final token and deadline. |

Receiver state is separate. A first delivery commits the receipt and effect
for the operation key. An identical delivery returns a duplicate result and
preserves both rows. A different payload for an already recorded key is
rejected. A lost acknowledgement can leave the effect committed while the
sender still reports a lease.

The tests compare return values and read all columns of the three SQLite
tables after each scheduled operation. The assertion code maps abstract lease
generations to tokens returned by the real outbox. It checks that each token
is fresh and that the stored token matches the one returned to the worker.
Each restart step creates fresh sender and receiver instances against the
same files and supplies the current authority again.

## Sequences

The generated matrix covers all 125 ordered combinations of five delivery
behaviors over three attempt slots. The behaviors are normal delivery,
transport outage, lost acknowledgement, duplicate frames, and a batch with a
valid frame followed by a changed payload. The slots fall five seconds apart.
After each slot the test reopens both databases and probes with a normal
attempt one second before the corresponding deadline. A final normal attempt
probes the end of the third lease. Earlier completion can make later slots
ineligible for a claim. The matrix includes exhaustion with an empty receiver
and exhaustion after receiver commit.

Focused traces cover acknowledgements before claim time, exactly at expiry,
with a wrong token, after reclaim with the previous token, and after completion.
They distinguish frame validation from the receiver's own rejection of a
changed payload. Revocation and replacement with a valid grant for a revised
payload both block retry of the original intent, including after reopening.
A separate fresh outbox confirms the replacement grant can deliver a claim
with the revised payload.

Two workers contend for one expired lease in each of two schedules, starting
after either an outage or a lost acknowledgement. The tests compare the
unordered claim results and the persisted state after both workers return.
They then check the old token and finish using the winning claim. The receiver
applies the effect after the outage and reports a duplicate after the lost
acknowledgement.

## Verification

Unittest and pytest collected the same **252 unique test methods**. Each
reported **247 passed, five skipped, and zero failed**. Pytest also reported
715 passing subtests, including 127 from Day 34. The five existing skips
require the private Day 23 raw archive. Its absence also prevented the
standalone sealed review from reading the archive manifest.

Day 13 metrics, Days 16–19 and 21–24 offline replays, all five public package
verifiers, the publication privacy scan, and Git whitespace checks passed.
The public verifiers report where private original-byte linkage is unavailable.
Historical evidence and frozen snapshots were preserved. Verification used
no model, cloud inference, or paid API calls.

## Limits

The matrix varies delivery outcomes on one fixed schedule for one operation.
It assumes trusted time, caller identity, and intact local storage. The two
worker races check the combined result of contention without controlling every
SQLite interleaving. Reopening workers tests committed state across instances.
The Day 33 suite separately exercises process interruption at selected commit
boundaries. Coverage here is bounded to the selected inputs and schedules.
Receiver deduplication depends on retaining the operation key and database,
and the separate sender acknowledgement can still be lost. The checks address
local SQLite effects and leave remote effects, storage loss, and power failure
outside their scope.
