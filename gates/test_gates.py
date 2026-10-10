"""test_gates.py -- real unit tests for the gate framework itself.

Run with: python test_gates.py
"""
from __future__ import annotations

import sys

from gates import Gate, Status
from example_usage import build_gate, CANARY_CASES


def test_rule_returns_pass_fail_unknown():
    gate = Gate("t")
    gate.register("always_pass", lambda d: (True, "ok"))
    gate.register("always_fail", lambda d: (False, "nope"))
    gate.register("always_unknown", lambda d: (None, "cannot tell"))
    report = gate.run({})
    statuses = {v.rule_name: v.status for v in report.verdicts}
    assert statuses["always_pass"] == Status.PASS
    assert statuses["always_fail"] == Status.FAIL
    assert statuses["always_unknown"] == Status.UNKNOWN


def test_strict_mode_blocks_on_fail_and_unknown():
    gate = Gate("t")
    gate.register("a", lambda d: (True, ""))
    gate.register("b", lambda d: (False, ""))
    assert gate.run({}).strict_ok() is False

    gate2 = Gate("t2")
    gate2.register("a", lambda d: (True, ""))
    gate2.register("b", lambda d: (None, ""))
    assert gate2.run({}).strict_ok() is False

    gate3 = Gate("t3")
    gate3.register("a", lambda d: (True, ""))
    gate3.register("b", lambda d: (True, ""))
    assert gate3.run({}).strict_ok() is True


def test_crashing_rule_is_unknown_not_pass():
    gate = Gate("t")

    def boom(d):
        raise ValueError("kaboom")

    gate.register("boom", boom)
    report = gate.run({})
    assert report.verdicts[0].status == Status.UNKNOWN


def test_example_canary_fixtures_all_verdict_correctly():
    gate = build_gate()
    ok, lines = gate.run_canary(CANARY_CASES)
    assert ok is True, "\n".join(lines)


def test_canary_catches_a_broken_rule():
    """If a rule is broken (e.g. always returns PASS), the canary must
    catch it -- this is the test for the test, proving run_canary itself
    can fail loudly rather than rubber-stamp."""
    gate = Gate("broken")
    gate.register("no_stub_marker", lambda d: (True, "broken: always passes"))
    cases = [("stub_article", {}, "no_stub_marker", Status.FAIL)]
    ok, lines = gate.run_canary(cases)
    assert ok is False
    assert "WRONG VERDICT" in lines[0]


def main() -> int:
    tests = [
        test_rule_returns_pass_fail_unknown,
        test_strict_mode_blocks_on_fail_and_unknown,
        test_crashing_rule_is_unknown_not_pass,
        test_example_canary_fixtures_all_verdict_correctly,
        test_canary_catches_a_broken_rule,
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
