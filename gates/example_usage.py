"""example_usage.py -- a worked example of the gates.py pattern.

Imagine a content pipeline that generates product-review articles. Before
any article is trusted, it must pass three independent rules:

  1. min_length    -- real articles are substantial, template stubs are not
  2. no_stub_marker -- demo/template output leaves a tell-tale marker behind
  3. has_price      -- a product article must state a price, or it is
                        presenting a product with no way to verify the claim

Run this file directly to see the canary run first (proving the rules
themselves work), then the gate run against a real-looking and a fake
article.
"""
from __future__ import annotations

import sys

from gates import Gate, Status, print_canary_result

STUB_MARKERS = ["TEMPLATE_STUB", "GENERATED_PLACEHOLDER"]


def rule_min_length(article: dict):
    words = len(article.get("text", "").split())
    if words < 50:
        return False, f"only {words} words (need 50+)"
    return True, f"{words} words"


def rule_no_stub_marker(article: dict):
    text = article.get("text", "")
    for marker in STUB_MARKERS:
        if marker in text:
            return False, f"contains stub marker '{marker}'"
    return True, "no stub markers found"


def rule_has_price(article: dict):
    price = article.get("price_usd")
    if price is None:
        return None, "no price field present -- cannot evaluate"
    if price <= 0:
        return False, f"price_usd={price} is not a real price"
    return True, f"price_usd={price}"


def build_gate() -> Gate:
    gate = Gate("article-quality")
    gate.register("min_length", rule_min_length)
    gate.register("no_stub_marker", rule_no_stub_marker)
    gate.register("has_price", rule_has_price)
    return gate


# --- canary fixtures: known-bad and known-good, proving the rules work -----
CANARY_CASES = [
    (
        "stub_article",
        {"text": "TEMPLATE_STUB " * 5, "price_usd": 19.99},
        "no_stub_marker",
        Status.FAIL,
    ),
    (
        "real_article",
        {"text": " ".join(["word"] * 120), "price_usd": 24.5},
        "no_stub_marker",
        Status.PASS,
    ),
    (
        "short_article",
        {"text": "too short", "price_usd": 10},
        "min_length",
        Status.FAIL,
    ),
    (
        "priced_article",
        {"text": " ".join(["word"] * 120), "price_usd": 24.5},
        "has_price",
        Status.PASS,
    ),
    (
        "unpriced_article",
        {"text": " ".join(["word"] * 120)},
        "has_price",
        Status.UNKNOWN,
    ),
]


def main() -> int:
    gate = build_gate()

    print("=== canary: proving the rules themselves still work ===")
    ok, lines = gate.run_canary(CANARY_CASES)
    rc = print_canary_result(ok, lines)
    if rc != 0:
        return rc

    print("\n=== gate run: a real-looking article ===")
    real = {"text": " ".join(["great", "product", "review"] * 60), "price_usd": 29.99}
    report = gate.run(real)
    print(report.summary())
    print("strict_ok:", report.strict_ok())

    print("\n=== gate run: a stub article ===")
    stub = {"text": "TEMPLATE_STUB", "price_usd": 0}
    report2 = gate.run(stub)
    print(report2.summary())
    print("strict_ok:", report2.strict_ok())

    return 0


if __name__ == "__main__":
    sys.exit(main())
