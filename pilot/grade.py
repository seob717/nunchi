#!/usr/bin/env python3
"""캡처된 PR을 pr-rules.md 4개 규칙으로 채점한다."""
import glob, json, os, re, sys

PILOT = os.path.dirname(os.path.abspath(__file__))

RULES = [
    ("제목 형식", lambda t, b: bool(re.match(r"^\[LAB-\d+\] (feat|fix|chore|docs|refactor): ", t or ""))),
    ("변경 이유 섹션", lambda t, b: "## 변경 이유" in (b or "")),
    ("테스트 계획 섹션", lambda t, b: "## 테스트 계획" in (b or "")),
    ("리뷰어 라인", lambda t, b: (b or "").rstrip().endswith("리뷰어: @seob")),
]

rows = []
for run_dir in sorted(glob.glob(os.path.join(PILOT, "runs", "*"))):
    label = os.path.basename(run_dir)
    captures = sorted(glob.glob(os.path.join(run_dir, "capture", "pr-*.json")))
    if not captures:
        rows.append((label, None, ["PR 미생성"] * len(RULES)))
        continue
    # 마지막 캡처 = 최종 제출본
    with open(captures[-1]) as f:
        pr = json.load(f)
    marks = [rule(pr.get("title"), pr.get("body")) for _, rule in RULES]
    rows.append((label, len(captures), marks))

print(f"{'런':<8} {'시도':<4} " + " ".join(f"{name:<10}" for name, _ in RULES) + " 점수")
totals = {}
for label, n, marks in rows:
    cond = label.split("-")[0]
    if marks[0] == "PR 미생성":
        print(f"{label:<8} {'-':<4} " + " ".join(f"{'미생성':<10}" for _ in RULES) + " 0/4")
        totals.setdefault(cond, []).append(0)
        continue
    score = sum(marks)
    cells = " ".join(f"{'✅' if m else '❌':<9}" for m in marks)
    print(f"{label:<8} {n:<4} {cells} {score}/4")
    totals.setdefault(cond, []).append(score)

print()
for cond, scores in sorted(totals.items()):
    pct = 100 * sum(scores) / (4 * len(scores)) if scores else 0
    print(f"조건 {cond}: 평균 준수율 {pct:.0f}%  (런별: {scores})")
