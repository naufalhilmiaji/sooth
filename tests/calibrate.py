"""Run the labeled calibration set (examples/calibration.json) against live Jev.

Usage: PYTHONPATH=src python3 tests/calibrate.py [--confidence T]

Exit 0 when score >= min_correct and no confident-wrong PASS on an expected FAIL.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # direct-run without install

from sooth.claims import Claim  # noqa: E402
from sooth.verify import PASS, verify_claims  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    args = sys.argv[1:]
    data = json.loads((ROOT / "examples" / "calibration.json").read_text(encoding="utf-8"))
    threshold = data["threshold"]
    if "--confidence" in args:
        threshold = float(args[args.index("--confidence") + 1])

    groups: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for case in data["cases"]:
        groups[tuple(case["source"])].append(case)

    rows = []
    for source_names, cases in groups.items():
        sources = [
            (name, (ROOT / "examples" / name).read_text(encoding="utf-8"))
            for name in source_names
        ]
        claims = [Claim(id=f"c{i + 1}", text=c["claim"], line=0) for i, c in enumerate(cases)]
        result = verify_claims(claims, sources, threshold=threshold)
        for case, verdict in zip(cases, result.verdicts):
            rows.append((case, verdict))

    correct = sum(1 for case, v in rows if case["expected"] == v.kind)
    total = len(rows)
    confident_wrong = [
        (case, v) for case, v in rows
        if case["expected"] == "FAIL" and v.kind == PASS and (v.confidence or 0) >= threshold
    ]

    print(f"threshold {threshold} — score {correct}/{total} (need {data['min_correct']})\n")
    keys = ("PASS", "FAIL", "REVIEW", "UNCHECKABLE")
    matrix = Counter((case["expected"], v.kind) for case, v in rows)
    print(f"{'exp\\got':<12}" + "".join(f"{k:>10}" for k in keys))
    for exp in keys:
        print(f"{exp:<12}" + "".join(f"{matrix[(exp, got)]:>10}" for got in keys))
    print()
    for case, v in rows:
        mark = "ok " if case["expected"] == v.kind else "ERR"
        print(f"{mark} {case['expected']:>11} <- {v.kind:<11} P={((v.confidence if v.kind != 'UNCHECKABLE' else v.p_checkable) or 0):.2f}"
              f"  [{','.join(case['source'])}] {case['claim'][:60]}")
        if case["expected"] != v.kind:
            print(f"      note: {case['note']}")
    if confident_wrong:
        print(f"\nHARD FAIL: {len(confident_wrong)} confident-wrong PASS(es) on contradicted claims")
        for case, v in confident_wrong:
            print(f"  - {case['claim']} (P={v.confidence:.2f})")
    return 0 if correct >= data["min_correct"] and not confident_wrong else 1


if __name__ == "__main__":
    raise SystemExit(main())
