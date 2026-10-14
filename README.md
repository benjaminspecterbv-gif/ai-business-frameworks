# AI Business Frameworks

Three small, working patterns for running AI agents as production
infrastructure rather than as a one-off script. They were extracted from
operating a real, small content/affiliate business where AI agents write,
check, and fix things autonomously — and where, more than once, an
unverified "it's done" claim turned out to be false. Each pattern exists
because one specific failure happened, got diagnosed, and got a permanent
guardrail instead of a one-time fix.

None of this is theoretical. Every folder has its own working code, its own
unit tests, and its own canary fixtures (deliberately-bad inputs the checks
must reject) — run them, don't just read them.

## The patterns

### [`gates/`](gates/) — verification gates that prove they still work
A small framework for registering independent PASS/FAIL/UNKNOWN rules against
generated content or data, with a `strict_ok()` mode where FAIL and UNKNOWN
both block. The key idea: a gate is not trusted until its **canary** —
known-bad and known-good fixtures run through the real rules — verdicts
correctly. A gate that has never rejected anything is not known to work.

### [`pipeline-contracts/`](pipeline-contracts/) — every pipeline describes itself before it runs
A YAML contract shape (artifact, provenance fields, independent oracles,
canary fixtures, liveness window, degrade behavior) plus a validator that
checks a pipeline run's manifest for internal *coherence*, not just presence
of fields — a run claiming zero cost and zero output tokens on a paid model
is rejected as forged, not accepted because the field existed.

### [`agent-orchestration/`](agent-orchestration/) — the fix agent is never the judge agent
A minimal orchestration shape: worklist → fix agent → independent judge agent
(never the same one) → exactly one repair round on failure → a report for a
human. The orchestrator never commits or publishes anything itself; it hands
a human the result.

## Why this exists

Running a small business with AI agents as part of the actual workforce
means the agents sometimes write the thing *and* the agents sometimes check
the thing — and the moment those two roles blur, reported progress stops
tracking reality. These three patterns are the guardrails that came out of
hitting that failure mode for real, generalized so they apply to any
AI-generated artifact, not just the specific business they were built for.

