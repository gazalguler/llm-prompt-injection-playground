# Day 25: trusted-source authorization boundary

2026-11-07 (America/Vancouver). Small offline development milestone.
No inference, paid calls, new model outputs or historical package changes.

`day25_authorization.py` wraps the unchanged Day 24 recovery. An independent,
owner-controlled policy explicitly grants one principal/task/incident/source
combination an exact revision, record digest and provenance reference. Every
supplied source must match a grant. Matching hashes and `authenticated=True`
alone cannot authorize an unlisted source. Missing, malformed and duplicate
grants abstain. Both snapshots retain Day 24 freshness, expiry, consistency and
revision checks. Policy revocation or any policy change before release abstains.
Successful outcomes identify the Day 25 policy and retain Day 24 provenance.

The caller must obtain policy, snapshots and trusted time independently of model
or retrieved text, and hold an authorization/revision lease through delivery.
This implements consistency against explicit synthetic authorization assertions,
not production authentication, signatures, identity verification or a live
revocation service. An attacker controlling trusted policy can authorize false
facts; a dedicated regression demonstrates this limitation. Hidden upstream
conflicts and changes after the final check remain external responsibilities.

Nine new test methods cover allowed release/provenance, all seven grant bindings,
spoofed source IDs with matching hashes, stale/future/expired snapshots, changed
revisions, revocation/policy changes, malformed grants, candidate instructions,
network prohibition and trusted poisoning. These are same-author development
regressions, not a held-out benchmark or improved model resistance. Existing
unittest discovery and pytest CI automatically include them.

Reproduce without a model server:

```sh
.venv/bin/python -B -S -m unittest tests.test_day25_authorization -v
.venv/bin/python -B -S -m unittest discover -s tests -t . -p 'test_*.py'
.venv/bin/python -B -m pytest tests -q -p no:cacheprovider
```

No new sealed publication package is claimed; all earlier packages remain intact.

Local validation: 167 unittest methods passed; pytest 167 passed and 485 subtests
passed. Day 13 metrics, Days 16–19/21–24 offline checks, all five historical public
package verifiers and the publication scanner passed. The scanner explicitly
includes the three new Day 25 files. No historical sealed bytes were edited.
