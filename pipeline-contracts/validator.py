"""validator.py -- checks a pipeline run's provenance manifest against a
declared contract (contract_schema.yaml shape).

The real problem this solves: a broken content pipeline reported a clean run
with invented numbers (zero cost, zero output tokens, no API request ids)
and nothing stopped it being treated as PASS. A manifest is a claim, not
evidence, until it is checked for internal coherence. This validator is that
check -- it does not need to call any API or know anything about the
pipeline's domain, it only needs the manifest and the list of required
fields.

Usage:
    python validator.py fixtures/good_run.json
    python validator.py fixtures/bad_run.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "producer",
    "producer_version",
    "model",
    "api_request_ids",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "wall_ms",
    "source_inputs",
    "fallbacks_fired",
    "generated_at",
]

TEMPLATE_MODEL_VALUE = "template"


def validate_manifest(manifest: dict) -> tuple:
    """Returns (verdict: 'PASS'|'FAIL'|'DEGRADED', reasons: list[str])."""
    reasons = []

    missing = [f for f in REQUIRED_FIELDS if f not in manifest]
    if missing:
        return "FAIL", [f"missing required field(s): {', '.join(missing)}"]

    model = manifest["model"]
    is_template = model == TEMPLATE_MODEL_VALUE

    # coherence rule: output_tokens == 0 AND artifact is non-trivial => forged
    if manifest["output_tokens"] == 0 and not is_template:
        reasons.append("output_tokens == 0 on a non-template model -- impossible, reject as forged")

    # coherence rule: fallbacks_fired non-empty => DEGRADED, never PASS
    degraded = bool(manifest["fallbacks_fired"])
    if degraded:
        reasons.append(f"fallbacks_fired non-empty: {manifest['fallbacks_fired']} -- DEGRADED")

    # coherence rule: api_request_ids empty AND model != template => forged
    if not manifest["api_request_ids"] and not is_template:
        reasons.append("api_request_ids empty on a non-template model -- forged")

    # coherence rule: cost_usd == 0.00 AND model != template => forged
    if manifest["cost_usd"] == 0.0 and not is_template:
        reasons.append("cost_usd == 0.00 on a non-template model -- forged")

    forged_reasons = [r for r in reasons if "forged" in r]
    if forged_reasons:
        return "FAIL", forged_reasons + [r for r in reasons if r not in forged_reasons]

    if degraded:
        return "DEGRADED", reasons

    return "PASS", ["manifest is complete and internally coherent"]


def main(argv: list) -> int:
    if len(argv) < 2:
        print("usage: python validator.py <manifest.json> [...]")
        return 2
    exit_code = 0
    for path_str in argv[1:]:
        path = Path(path_str)
        manifest = json.loads(path.read_text(encoding="utf-8"))
        verdict, reasons = validate_manifest(manifest)
        print(f"{path.name}: {verdict}")
        for r in reasons:
            print(f"  - {r}")
        if verdict == "FAIL":
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
