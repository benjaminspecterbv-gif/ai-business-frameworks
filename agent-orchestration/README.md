# agent-orchestration — fix agent is never the judge agent

## The problem this solves

An automated "improve this" workflow had one agent fix an issue and then
grade its own fix. It passed almost everything — because an agent checking
its own work tends to confirm its own intention, not discover what's
actually still wrong. Reported progress didn't match reality, and nobody
could tell from the reports alone.

The fix is a small, strict orchestration shape:

1. Pull a worklist (measured from the real system, never from a stale log).
2. Per item: a **fix agent** acts on it.
3. A **separate, independent judge agent** evaluates the result — seeing
   only the resulting state, never the fix agent's reasoning or what it was
   "supposed" to do. It cannot confirm an intention it was never shown.
4. On judge FAIL: exactly **one** repair round, informed by the judge's
   findings. Win or lose, the loop stops there — looping forever on a
   stubborn item is a signal that the rule itself is wrong, which is a
   decision for a human, not something to retry into submission.
5. **Nothing here ever commits or publishes.** The orchestrator returns a
   report; a human reads the diff and decides.

`orchestrator.py`'s `run_pipeline()` even raises immediately if `fix_agent`
and `judge_agent` are literally the same callable — the most common way this
mistake gets made by accident.

## Usage

```python
from orchestrator import WorkItem, run_pipeline, summarize

worklist = [WorkItem(id="page-1", payload={"value": 3})]

reports = run_pipeline(worklist, my_fix_agent, my_judge_agent)
print(summarize(reports))
```

`my_fix_agent` and `my_judge_agent` are plain functions — swap the fake ones
in `test_orchestrator.py` for real LLM calls (different prompts/models for
fix vs. judge) without touching the orchestration logic itself.

Run the tests (all use fake, deterministic agents — no network or API key
needed):

```
python test_orchestrator.py
```

The tests prove, concretely: a halted fix never reaches the judge; a FAIL
triggers exactly one repair round and the judge's findings are actually
visible to the repair attempt; using the same function for both roles raises
instead of silently producing a meaningless "PASS"; and the final summary
always tells the human to commit — the orchestrator itself never does.
