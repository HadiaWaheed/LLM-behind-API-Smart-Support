import json
from pathlib import Path

import requests


BASE_URL = "http://127.0.0.1:8000"

CASES_PATH = (
    Path(__file__).parent
    / "cases.json"
)

RESULTS_PATH = (
    Path(__file__).parent
    / "results.json"
)


def run_case(case):
    response = requests.post(
        f"{BASE_URL}/triage",
        json={
            "text": case["text"]
        },
        timeout=30,
    )

    result = {
        "id": case["id"],
        "text": case["text"],
        "status_code": response.status_code,
        "passed": False,
    }

    if response.status_code != 200:
        result["error"] = response.text
        return result

    actual = response.json()
    expected = case["expected"]

    result["actual"] = actual
    result["expected"] = expected

    # Compare only the fields we explicitly expect.
    result["passed"] = all(
        actual.get(field) == expected[field]
        for field in expected
    )

    return result


def main():

    with CASES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        cases = json.load(file)

    results = []

    for case in cases:

        print(
            f"Running {case['id']}..."
        )

        result = run_case(case)

        results.append(result)

        if result["passed"]:
            print("  PASS")
        else:
            print("  FAIL")

    passed = sum(
        result["passed"]
        for result in results
    )

    total = len(results)

    summary = {
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": (
            passed / total
            if total
            else 0
        ),
    }

    output = {
        "summary": summary,
        "results": results,
    }

    with RESULTS_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("================================")
    print("EVALUATION COMPLETE")
    print("================================")
    print(
        f"Total: {total}"
    )
    print(
        f"Passed: {passed}"
    )
    print(
        f"Failed: {total - passed}"
    )
    print(
        f"Pass rate: {summary['pass_rate']:.2%}"
    )


if __name__ == "__main__":
    main()