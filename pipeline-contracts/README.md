# pipeline-contracts — every AI pipeline describes itself before it may run

## The problem this solves

A content generator produced a "completed, clean" run with zero API request
ids, zero cost, and zero output tokens on a model that is never free. Nobody
had defined what a *coherent* run manifest looks like, so nothing caught it:
the run silently looked identical to a real one until someone noticed the
cost ledger hadn't moved in days. By the time that noticed, a backlog of
unverifiable "finished" artifacts had already been treated as done.

The fix: **no pipeline that writes output may run without a declared
contract**, and every run must produce a provenance manifest that is checked
for internal coherence, not just presence of fields.

- `contract_schema.yaml` — the shape a pipeline contract takes: what it
  produces, the required provenance fields, independent oracles (each states
  its own independence basis — an oracle built from the same spec as the
  generator doesn't count), canary fixtures the validator must never
  mis-verdict, a liveness window, and explicit degrade behavior (never
  "substitute silently").
- `validator.py` — reads a run's manifest and returns PASS / FAIL / DEGRADED
  plus the reasons. It encodes the coherence rules directly:
  - `output_tokens == 0` on a non-template model → impossible → FAIL
  - `api_request_ids` empty on a non-template model → forged → FAIL
  - `cost_usd == 0.00` on a non-template model → forged → FAIL
  - `fallbacks_fired` non-empty → DEGRADED, never PASS
- `fixtures/` — known-good, known-bad (forged cost), missing-fields, a
  degraded (fallback-fired) run, and a zero-output-tokens run. `test_validator.py`
  asserts the validator verdicts every one of them correctly.

## Usage

```
python validator.py fixtures/good_run.json
python validator.py fixtures/bad_run.json
python test_validator.py
```

```python
from validator import validate_manifest
import json

manifest = json.loads(open("run_12345.manifest.json").read())
verdict, reasons = validate_manifest(manifest)
if verdict != "PASS":
    raise SystemExit(f"run rejected: {verdict} -- {reasons}")
```

A pipeline with no contract file next to it, or a run whose manifest fails
`validate_manifest`, does not get to publish. That gate is the whole point —
cost and token counts are the hardest things for a broken pipeline to fake
convincingly, so that's exactly what gets checked.
