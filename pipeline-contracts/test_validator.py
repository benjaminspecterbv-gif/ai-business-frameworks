"""test_validator.py -- real tests proving validator.py actually catches the
forged/incoherent manifests, not just that it runs.

Run with: python test_validator.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from validator import validate_manifest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_good_run_passes():
    verdict, reasons = validate_manifest(load("good_run.json"))
    assert verdict == "PASS", reasons


def test_bad_run_fails_zero_cost():
    verdict, reasons = validate_manifest(load("bad_run.json"))
    assert verdict == "FAIL", reasons
    assert any("cost_usd" in r or "forged" in r for r in reasons), reasons


def test_missing_fields_fails():
    verdict, reasons = validate_manifest(load("missing_fields.json"))
    assert verdict == "FAIL", reasons
    assert any("missing required field" in r for r in reasons), reasons


def test_degraded_run_is_degraded_not_pass():
    verdict, reasons = validate_manifest(load("degraded_run.json"))
    assert verdict == "DEGRADED", reasons


def test_zero_output_tokens_fails():
    verdict, reasons = validate_manifest(load("zero_output_tokens.json"))
    assert verdict == "FAIL", reasons
    assert any("output_tokens" in r for r in reasons), reasons


def test_template_model_is_exempt_from_cost_and_token_rules():
    manifest = load("good_run.json").copy()
    manifest["model"] = "template"
    manifest["cost_usd"] = 0.0
    manifest["output_tokens"] = 0
    manifest["api_request_ids"] = []
    verdict, reasons = validate_manifest(manifest)
    assert verdict == "PASS", reasons


def main() -> int:
    tests = [
        test_good_run_passes,
        test_bad_run_fails_zero_cost,
        test_missing_fields_fails,
        test_degraded_run_is_degraded_not_pass,
        test_zero_output_tokens_fails,
        test_template_model_is_exempt_from_cost_and_token_rules,
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
        except AssertionError as ex:
            print(f"[FAIL] {t.__name__}: {ex}")
            failures += 1
    if failures:
        print(f"\n{failures} test(s) failed")
    else:
        print(f"\nAll {len(tests)} tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
