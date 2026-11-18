"""Milestone A2 check: does the assistant get 5 questions right?

The expected answers are the verified numbers from the Data Analyst project and the
pipeline's dbt regression test (Q2 2024), plus the pipeline's Q2 2026 results.

  python3 eval_a2.py
"""
import re
import time

from assistant import ask

# (question, patterns that must ALL appear, patterns that must NOT appear in the lead sentence)
CASES = [
    (
        "What was the national weighted HPRD in Q2 2024?",
        [r"\b3\.30?\b"],
        [r"\b3\.29\b"],  # 3.29 = reporting-gap facilities wrongly included
    ),
    (
        "Which state had the lowest weighted HPRD in Q2 2024, and what was it?",
        [r"Missouri", r"\b2\.42\b"],
        [],
    ),
    (
        "Which state relied most on contract nursing staff in Q2 2024, as a share of nurse hours?",
        [r"Vermont", r"\b(31\.[5-9]|32(\.[0-4])?)\s?%"],
        [],
    ),
    (
        "What percentage of facilities had a weighted HPRD below 3.0 in Q2 2024?",
        [r"\b34(\.[0-5])?\s?%"],  # 5,011 / 14,544 = 34.45% (pipeline test rounds to 34%)
        [],
    ),
    (
        "How did national weighted HPRD change from Q2 2024 to Q2 2026?",
        # 2026Q2 is 3.3750 to 4 decimals, right on the rounding boundary, so 3.37 and 3.38 both count
        [r"\b3\.30?\b", r"\b3\.3[78]\b"],
        [],
    ),
]


def main() -> None:
    passed = 0
    for n, (question, patterns, forbidden) in enumerate(CASES, 1):
        start = time.time()
        result = ask(question)
        seconds = time.time() - start
        missing = [p for p in patterns if not re.search(p, result["answer"], re.IGNORECASE)]
        lead = result["answer"].strip().split("\n")[0]  # the headline answer; side notes may mention other values
        wrong = [p for p in forbidden if re.search(p, lead, re.IGNORECASE)]
        ok = not missing and not wrong
        passed += ok
        errors = sum("error" in q for q in result["queries"])

        print(f"\n[{'PASS' if ok else 'FAIL'}] Q{n}: {question}")
        print(f"  Answer: {result['answer']}")
        print(f"  Queries: {len(result['queries'])} ({errors} with errors), {seconds:.1f}s")
        if missing or wrong:
            if missing:
                print(f"  Missing expected: {missing}")
            if wrong:
                print(f"  Headline has a wrong value: {wrong}")
            for q in result["queries"]:
                print("  SQL:", q["sql"].replace("\n", " ")[:300])

    print(f"\nScore: {passed}/{len(CASES)}")


if __name__ == "__main__":
    main()
