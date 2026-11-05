# Day 24 proposal: owner-controlled structured-fact recovery

**Design proposal only. No implementation, experiments, new output examples or
inference are part of Day 23.** The Day 23 negative result and all original labels
remain unchanged. This proposal is informed by those observed failures; evaluating
it on those same outputs would be development replay, not independent validation.

Day 23 showed that a narrow natural-language acceptance grammar can contain
compromised answers while rejecting useful paraphrases. A recovery path should
avoid dependence on the model's choice of English phrasing. When the caller
already has authoritative structured incident facts and an authorized narrow
summary task, a deterministic renderer can produce the requested statement from
those facts under a separate, explicit release policy.

## Proposed trust boundary and control flow

1. Trusted application code authenticates the source and authorizes the user's
   task. It selects one current incident record and independently pins record ID,
   schema version and revision. It resolves stale/conflicting records upstream,
   enforces access policy and binds the record to this request. A matching ID or
   hash is a consistency check, not authentication.
2. Validate an exact typed record: bounded duration with explicit units, a finite
   allowed component identifier, and an explicit supported relation that a restart
   of that component restored service. Require source/provenance and freshness
   policy in trusted metadata. Reject missing/extra fields, competing values,
   booleans masquerading as numbers, unsupported relations and wrong pins. Do not
   invent outage cause, data-loss status or intervention details from correlation.
3. Treat model-generated text and retrieved/tool content as untrusted. Neither may
   choose or replace the trusted record, task, revision, template, policy or routing.
   If an LLM performs extraction upstream, its result remains a candidate requiring
   trusted validation; it cannot promote its own assertions into owner facts.
4. Preserve the candidate and its containment decision for the audit trail. On
   rejection, discard its contents completely for recovery. If the authorized task
   can be fully answered by validated structured facts, use an owner-controlled
   template selected by task/schema policy. Render only validated numeric values
   and mapped finite identifiers; never concatenate free-form retrieved text,
   instructions, arbitrary record labels or model-provided template fragments.
5. Validate the renderer's typed result and deterministic template selection under
   the same record snapshot/pins. Record fact/policy/template version and digest,
   original candidate decision, recovery disposition and provenance. If the task
   asks for unsupported context, facts conflict, authorization fails or a record
   changes mid-request, withhold; do not pretend a partial incident sentence answers
   the broader task. Recheck authorization/current revision before release.

For this narrow task class, rendering directly from trusted facts may be preferable
to generating an unnecessary model candidate. If the evaluation retains an LLM to
measure attack susceptibility, the renderer is a distinct application recovery
mechanism. It does not mean the model resisted an attack. No repair-model call,
automatic regeneration or untrusted text cleanup is needed in the proposed path.

## Release contract and limits

The owner must authorize this recovery policy before deployment. A blocked model
candidate does not itself authorize synthesis. The response should identify itself
as a system-rendered summary of the selected trusted record, with permitted source
provenance when useful. It must not suggest it reflects the model's original answer.
A renderer cannot authenticate real-world truth, resolve hidden upstream conflicts
or correct poisoned owner records. Trusted selection, access control, freshness,
consistent snapshots and explicit relations remain essential. Unsupported tasks
should abstain rather than force every request into an incident template.

This changes where legitimate completion comes from: containment and completion
must be measured separately. It is not a broader natural-language entailment gate
and does not make the existing Day 22 gate general-purpose.

## Future evaluation proposal

Before future execution, freeze the schema, trusted-source/routing contract,
renderer policy, template version, plan and success criteria. Use independent
new attack/control payloads and incident records after development, with explicit
approval for any inference. A no-inference deterministic test suite could first
exercise wrong-task/revision routing, stale/conflicting facts, missing fields,
malformed types, untrusted template selection, free-form slot contamination,
unsupported cause assertions, concurrent revision changes and unauthorized users.
These are proposed tests, not Day 23 results.

Keep model full/partial success and resistance; original candidate gate blocks;
recovery eligibility, release and abstention; false release of unsupported facts;
clean false abstention; and final authorized factual completion as separate counts
with explicit denominators. Include controls requesting information absent from
the record, so forced completion cannot appear successful. Retain both the
original candidate and separately labeled rendered response. Independent human
review and new held-out data would strengthen claims; this design alone supplies
no evidence of safety or utility gains.
