#!/usr/bin/env python3
"""보수적 채점기 — 낙관 편향을 제거한 엄격 기준.

grade.py 와의 차이:
1. 제목: 줄 전체가 형식과 일치해야 함 (부분 매치 불가), 설명부가 비어 있으면 실패
2. 섹션: 헤딩 존재 + 헤딩 아래 실제 내용 10자 이상 (빈 섹션은 실패)
3. 리뷰어: 마지막 비어있지 않은 줄이 정확히 "리뷰어: @seob" (endswith 부분 매치 불가)
4. 런 단위 판정: 4개 규칙 전부 통과해야 성공 (부분 점수 없음)
5. Wilson 95% 신뢰구간 보고 (n이 작다는 걸 숨기지 않기)
"""
import glob, json, math, os, re

PILOT = os.path.dirname(os.path.abspath(__file__))


def section_content(body, heading):
    m = re.search(re.escape(heading) + r"\n(.*?)(?=\n## |\Z)", body or "", re.S)
    if not m:
        return None
    return m.group(1).strip()


def check_title(t, b):
    if not t:
        return False
    if not re.fullmatch(r"\[LAB-123\] (feat|fix|chore|docs|refactor): .+", t.strip()):
        return False
    desc = t.split(":", 1)[1].strip()
    return len(desc) >= 2


def check_reason(t, b):
    c = section_content(b, "## 변경 이유")
    return c is not None and len(c) >= 10


def check_test_plan(t, b):
    c = section_content(b, "## 테스트 계획")
    return c is not None and len(c) >= 10


def check_reviewer(t, b):
    lines = [l.strip() for l in (b or "").splitlines() if l.strip()]
    return bool(lines) and lines[-1] == "리뷰어: @seob"


RULES = [
    ("제목(엄격)", check_title),
    ("변경 이유(내용)", check_reason),
    ("테스트 계획(내용)", check_test_plan),
    ("리뷰어(정확)", check_reviewer),
]


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


totals = {}
print(f"{'런':<8} " + " ".join(f"{name:<12}" for name, _ in RULES) + " 전부통과")
for run_dir in sorted(glob.glob(os.path.join(PILOT, "runs", "*"))):
    label = os.path.basename(run_dir)
    cond = label.split("-")[0]
    captures = sorted(glob.glob(os.path.join(run_dir, "capture", "pr-*.json")))
    if not captures:
        print(f"{label:<8} " + " ".join(f"{'미생성':<12}" for _ in RULES) + " ❌")
        totals.setdefault(cond, []).append(False)
        continue
    with open(captures[-1]) as f:
        pr = json.load(f)
    marks = [fn(pr.get("title"), pr.get("body")) for _, fn in RULES]
    ok = all(marks)
    cells = " ".join(f"{'✅' if m else '❌':<11}" for m in marks)
    print(f"{label:<8} {cells} {'✅' if ok else '❌'}")
    totals.setdefault(cond, []).append(ok)

print()
for cond, results in sorted(totals.items()):
    k, n = sum(results), len(results)
    lo, hi = wilson_ci(k, n)
    print(f"조건 {cond}: {k}/{n} 전부통과  (Wilson 95% CI: {lo*100:.0f}%–{hi*100:.0f}%)")
print("\n주의: n=3은 탐색용 표본이다. CI 하한이 보여주듯 '100%'는 '이 표본에서 실패를 못 봤다' 이상을 의미하지 않는다.")
print("B의 수치는 '주입 후 재시도'의 준수율이다. 1차 시도는 실행 전에 차단되므로 측정 대상이 아니다.")
