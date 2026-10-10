# gates — a generic verification-gate framework

## The problem this solves

An automated content/data pipeline reported its own output as clean. Nobody
had ever proven that the check doing the reporting could actually tell a
broken artifact from a good one — it had simply never been pointed at a
known-bad fixture. When it finally was, it turned out to rubber-stamp
everything: a gate that has never rejected anything is not a gate, it's a
formality.

The fix is two separate pieces, both in this folder:

1. **Rules return PASS / FAIL / UNKNOWN**, never just a boolean. `UNKNOWN`
   covers "this check could not run" (missing input, a crash, a blocked
   dependency) and it is never silently folded into PASS. In `strict_ok()`
   mode, FAIL and UNKNOWN both block.
2. **The canary runs before the gate is trusted.** `run_canary()` feeds
   known-bad and known-good fixtures through the real rules and asserts the
   verdict is what it should be. If the canary doesn't pass, the gate is not
   used against real data that run — full stop.

## Usage

```python
from gates import Gate, Status

gate = Gate("article-quality")
gate.register("min_length", lambda a: (len(a["text"].split()) >= 50, "..."))
gate.register("has_price", lambda a: (a.get("price_usd", 0) > 0, "..."))

# 1. prove the rules work, every run, before trusting real data
ok, lines = gate.run_canary([
    ("stub", {"text": "x"}, "min_length", Status.FAIL),
    ("real", {"text": "..." * 100}, "min_length", Status.PASS),
])
if not ok:
    raise SystemExit("gate canary failed -- do not trust this gate")

# 2. only now run it against real input
report = gate.run(real_article)
print(report.strict_ok())   # True only if every rule PASSed
```

See `example_usage.py` for a full worked example (a fake article-quality
gate with three rules) and `test_gates.py` for the tests that prove the
framework itself behaves — including a test that a broken rule (one that
always returns PASS) gets caught by the canary mechanism, not silently
trusted.

Run it:

```
python test_gates.py
python example_usage.py
```
