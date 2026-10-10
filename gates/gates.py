"""gates.py -- a small, generic verification-gate framework.

The pattern this encodes: an automated pipeline produces artifacts (text,
HTML, JSON, whatever). Before anything downstream trusts an artifact, a set
of independent *rules* each verdict it PASS / FAIL / UNKNOWN. The gate only
clears an artifact in "strict mode" if every rule returns PASS or UNKNOWN is
treated as a hard stop for whoever is reading the report (never silently
collapsed into PASS).

Critically: a gate that has never rejected anything is not known to work. So
this module also carries a `Canary` concept -- a set of known-bad and
known-good fixtures that must verdict correctly BEFORE the gate is trusted
against real input. Run the canary first, every time, not just once at
launch.

This is deliberately content-agnostic: `data` can be a string, a dict, a
path, anything. Rules just need to accept whatever shape the caller chooses
and return a Verdict.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable


class Status(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"   # a blocked check, a timeout, missing input --
                          # NEVER silently counted as a failure or a pass.


@dataclass
class Verdict:
    rule_name: str
    status: Status
    detail: str = ""


@dataclass
class Rule:
    """A single independent check. `fn(data) -> (bool | None, detail)`.

    fn should return:
        (True, detail)  -> PASS
        (False, detail) -> FAIL
        (None, detail)  -> UNKNOWN (could not evaluate -- say so, don't guess)
    """
    name: str
    fn: Callable[[Any], tuple]

    def run(self, data: Any) -> Verdict:
        try:
            ok, detail = self.fn(data)
        except Exception as ex:          # noqa: BLE001 -- a crashing rule is UNKNOWN, not a pass
            return Verdict(self.name, Status.UNKNOWN, f"rule raised: {ex}")
        if ok is True:
            return Verdict(self.name, Status.PASS, detail)
        if ok is False:
            return Verdict(self.name, Status.FAIL, detail)
        return Verdict(self.name, Status.UNKNOWN, detail)


@dataclass
class GateReport:
    verdicts: list = field(default_factory=list)

    @property
    def failed(self) -> list:
        return [v for v in self.verdicts if v.status == Status.FAIL]

    @property
    def unknown(self) -> list:
        return [v for v in self.verdicts if v.status == Status.UNKNOWN]

    def strict_ok(self) -> bool:
        """Strict mode: every rule must PASS. FAIL or UNKNOWN both block."""
        return all(v.status == Status.PASS for v in self.verdicts)

    def summary(self) -> str:
        lines = []
        for v in self.verdicts:
            lines.append(f"[{v.status.value:7}] {v.rule_name}: {v.detail}")
        return "\n".join(lines)


class Gate:
    """Registers rules, runs them against data, and -- separately -- against
    canary fixtures to prove the rules themselves still work."""

    def __init__(self, name: str):
        self.name = name
        self.rules: list = []

    def register(self, name: str, fn: Callable[[Any], tuple]) -> None:
        self.rules.append(Rule(name, fn))

    def run(self, data: Any) -> GateReport:
        return GateReport(verdicts=[r.run(data) for r in self.rules])

    def run_canary(self, canary_cases: Iterable) -> tuple:
        """canary_cases: iterable of (case_name, data, rule_name, expected_status).

        Returns (ok: bool, report_lines: list[str]). A single mismatch makes
        ok False -- the gate cannot be trusted this run.
        """
        by_name = {r.name: r for r in self.rules}
        ok = True
        lines = []
        for case_name, data, rule_name, expected in canary_cases:
            rule = by_name.get(rule_name)
            if rule is None:
                ok = False
                lines.append(f"[MISSING] rule '{rule_name}' not registered -- cannot test {case_name}")
                continue
            verdict = rule.run(data)
            got = verdict.status
            mark = "OK  " if got == expected else "WRONG VERDICT"
            if got != expected:
                ok = False
            lines.append(
                f"[{mark}] {case_name} / {rule_name}: expected {expected.value}, "
                f"got {got.value} ({verdict.detail})"
            )
        return ok, lines


def print_canary_result(ok: bool, lines: list) -> int:
    print("\n".join(lines))
    if ok:
        print("\nAll canaries verdict correctly. Gate is known-good for this run.")
        return 0
    print("\nCanary failure(s) -- the gate cannot be trusted. Do not run it against real data yet.")
    return 1
