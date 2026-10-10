"""test_orchestrator.py -- real tests for the fix/judge orchestration
pattern, using fake agent functions so no network/LLM call is needed.

Run with: python test_orchestrator.py
"""
from __future__ import annotations

import sys

from orchestrator import (
    FixResult,
    JudgeResult,
    Verdict,
    WorkItem,
    run_pipeline,
    summarize,
)


# --- fake agents for testing -------------------------------------------

def fix_agent_always_fixes(item: WorkItem) -> FixResult:
    """Pretends to fix the item by setting value >= 10."""
    new_value = max(item.payload.get("value", 0), 10)
    return FixResult(item.id, "fixed", "raised value to >= 10", {"value": new_value})


def fix_agent_never_fixes(item: WorkItem) -> FixResult:
    """A broken fix agent that never actually changes anything."""
    return FixResult(item.id, "fixed", "no-op", dict(item.payload))


def judge_agent_checks_threshold(item: WorkItem, fix: FixResult) -> JudgeResult:
    """Independent judge: PASS only if the resulting value >= 10."""
    value = fix.new_state.get("value", 0)
    if value >= 10:
        return JudgeResult(item.id, Verdict.PASS, [])
    return JudgeResult(item.id, Verdict.FAIL, [f"value {value} is still below 10"])


def test_happy_path_all_pass():
    worklist = [WorkItem(id="a", payload={"value": 3}), WorkItem(id="b", payload={"value": 20})]
    reports = run_pipeline(worklist, fix_agent_always_fixes, judge_agent_checks_threshold)
    assert all(r.status == "PASS" for r in reports), reports
    assert all(not r.repaired for r in reports)


def test_judge_rejects_then_one_repair_round_fixes_it():
    """fix_agent_never_fixes fails the judge the first time, but the repair
    round (still using fix_agent_never_fixes) will ALSO fail -- proving the
    repair round runs and the loop still reports FAIL rather than looping
    forever or silently passing."""
    worklist = [WorkItem(id="x", payload={"value": 1})]
    reports = run_pipeline(worklist, fix_agent_never_fixes, judge_agent_checks_threshold)
    assert len(reports) == 1
    r = reports[0]
    assert r.repaired is True, "the repair round should have run after the first FAIL"
    assert r.status == "FAIL", "a broken fix agent must still end as FAIL, never silently PASS"


def test_repair_round_actually_uses_judge_findings_to_succeed():
    """A fix agent that only fixes correctly once it sees judge_findings in
    its payload -- proving the repair round's instruction actually carries
    the judge's findings forward."""

    def smart_fix(item: WorkItem) -> FixResult:
        if "judge_findings" in item.payload:
            return FixResult(item.id, "fixed", "repaired using judge findings", {"value": 99})
        return FixResult(item.id, "fixed", "first attempt, deliberately wrong", {"value": 1})

    worklist = [WorkItem(id="y", payload={"value": 1})]
    reports = run_pipeline(worklist, smart_fix, judge_agent_checks_threshold)
    r = reports[0]
    assert r.repaired is True
    assert r.status == "PASS", "repair round should have succeeded using judge findings"


def test_fix_agent_and_judge_agent_must_differ():
    same_fn = fix_agent_always_fixes
    worklist = [WorkItem(id="z", payload={"value": 1})]
    try:
        run_pipeline(worklist, same_fn, same_fn)
        raised = False
    except ValueError:
        raised = True
    assert raised, "using the same callable for fix and judge must raise"


def test_halted_item_skips_judge_entirely():
    def fix_that_halts(item: WorkItem) -> FixResult:
        return FixResult(item.id, "halted", "could not safely fix", dict(item.payload))

    judge_called = {"count": 0}

    def judge_that_counts(item: WorkItem, fix: FixResult) -> JudgeResult:
        judge_called["count"] += 1
        return JudgeResult(item.id, Verdict.PASS, [])

    worklist = [WorkItem(id="h", payload={})]
    reports = run_pipeline(worklist, fix_that_halts, judge_that_counts)
    assert reports[0].status == "HALTED"
    assert judge_called["count"] == 0, "a halted fix must never reach the judge"


def test_summarize_tallies_and_never_mentions_committing_as_done():
    worklist = [WorkItem(id="a", payload={"value": 20})]
    reports = run_pipeline(worklist, fix_agent_always_fixes, judge_agent_checks_threshold)
    summary = summarize(reports)
    assert summary["tally"]["PASS"] == 1
    assert any("commit" in s for s in summary["human_still_to_do"])


def main() -> int:
    tests = [
        test_happy_path_all_pass,
        test_judge_rejects_then_one_repair_round_fixes_it,
        test_repair_round_actually_uses_judge_findings_to_succeed,
        test_fix_agent_and_judge_agent_must_differ,
        test_halted_item_skips_judge_entirely,
        test_summarize_tallies_and_never_mentions_committing_as_done,
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
