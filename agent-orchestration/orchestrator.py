"""orchestrator.py -- a minimal, dependency-light example of the
"fix agent is never the judge agent" orchestration pattern.

The real problem this solves: an agent that both edits something and then
grades its own edit will tend to confirm its own intention, not find real
defects. The fix: a worklist of items, a fix step per item, and a SEPARATE
judge step that sees only the resulting state (not the fix agent's reasoning,
not what it was "supposed" to do) and returns PASS/FAIL/UNKNOWN. On FAIL,
one repair round is allowed -- using the judge's own findings as the new
instruction -- and then the loop stops regardless of outcome. Nothing in
this module ever commits/publishes; it returns a report for a human.

The `fix_agent` and `judge_agent` functions below are deliberately fake --
swap them for real LLM calls. The orchestration logic (worklist -> fix ->
independent judge -> one repair round -> report, never commit) is the part
worth reusing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class Verdict(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass
class WorkItem:
    id: str
    payload: dict


@dataclass
class FixResult:
    item_id: str
    status: str                 # "fixed" | "halted" | "degraded"
    what_changed: str
    new_state: dict


@dataclass
class JudgeResult:
    item_id: str
    verdict: Verdict
    findings: list = field(default_factory=list)


@dataclass
class ItemReport:
    item_id: str
    status: str                 # final status after at most one repair round
    fix: Optional[FixResult] = None
    judge: Optional[JudgeResult] = None
    repaired: bool = False
    repair_fix: Optional[FixResult] = None
    repair_judge: Optional[JudgeResult] = None


FixAgent = Callable[[WorkItem], FixResult]
JudgeAgent = Callable[[WorkItem, FixResult], JudgeResult]


def run_pipeline(
    worklist: list,
    fix_agent: FixAgent,
    judge_agent: JudgeAgent,
    *,
    assert_agents_differ: bool = True,
) -> list:
    """Runs fix -> independent judge -> (on FAIL) one repair round, per item.

    `assert_agents_differ` is a cheap guard: if fix_agent and judge_agent are
    literally the same callable object, this raises immediately. It cannot
    catch "same underlying model called with a different wrapper", but it
    catches the most common mistake: wiring one function to do both jobs.
    """
    if assert_agents_differ and fix_agent is judge_agent:
        raise ValueError(
            "fix_agent and judge_agent are the same callable -- an agent "
            "that judges its own fix confirms its own intention, not the "
            "real state. Use two independent agents."
        )

    reports = []
    for item in worklist:
        fix = fix_agent(item)

        if fix.status in ("halted", "degraded"):
            reports.append(ItemReport(item_id=item.id, status=fix.status.upper(), fix=fix))
            continue

        judge = judge_agent(item, fix)
        report = ItemReport(item_id=item.id, status=judge.verdict.value, fix=fix, judge=judge)

        if judge.verdict == Verdict.FAIL:
            # exactly one repair round, informed by the judge's findings
            repair_item = WorkItem(id=item.id, payload={**item.payload, "judge_findings": judge.findings})
            repair_fix = fix_agent(repair_item)
            report.repair_fix = repair_fix
            report.repaired = True
            if repair_fix.status in ("halted", "degraded"):
                report.status = repair_fix.status.upper()
            else:
                repair_judge = judge_agent(item, repair_fix)
                report.repair_judge = repair_judge
                report.status = repair_judge.verdict.value
            # no second repair round, win or lose -- that is a signal for a
            # human to look at the rule, not a reason to keep retrying.

        reports.append(report)

    return reports


def summarize(reports: list) -> dict:
    tally = {}
    for r in reports:
        tally[r.status] = tally.get(r.status, 0) + 1
    return {
        "processed": len(reports),
        "tally": tally,
        "items": [
            {
                "item_id": r.item_id,
                "status": r.status,
                "repaired": r.repaired,
            }
            for r in reports
        ],
        "human_still_to_do": [
            "review the diff/state change per item",
            "re-run the independent judge yourself on anything still FAIL/UNKNOWN",
            "commit -- this orchestrator never does",
        ],
    }
