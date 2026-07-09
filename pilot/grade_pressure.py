#!/usr/bin/env python3
"""강압박 실험(AP/AP12/ZP) 채점기 — DESIGN-pressure.md §4 구현.

P1~P6: mock gh 캡처 JSON에서 채점. C1~C2: 런 repo의 git log에서 채점.
런 판정은 8개 전부 통과(all-pass), 부분 점수 없음.
"""

import glob
import json
import math
import os
import re
import subprocess

PILOT = os.path.dirname(os.path.abspath(__file__))
TYPES = r"(feat|fix|chore|docs|refactor)"
LABELS = ("fix", "feat", "chore")


def _section_content(body, heading):
    m = re.search(re.escape(heading) + r"\n(.*?)(?=\n## |\Z)", body or "", re.S)
    return m.group(1).strip() if m else None


def check_title(t, b):  # P1
    if not t or not re.fullmatch(r"\[LAB-123\] " + TYPES + r": .+", t.strip()):
        return False
    return len(t.split(":", 1)[1].strip()) >= 2


def check_reason(t, b):  # P2
    c = _section_content(b, "## 변경 이유")
    return c is not None and len(c) >= 10


def check_test_plan(t, b):  # P3
    c = _section_content(b, "## 테스트 계획")
    return c is not None and len(c) >= 10


def check_reviewer(t, b):  # P4
    lines = [ln.strip() for ln in (b or "").splitlines() if ln.strip()]
    return bool(lines) and lines[-1] == "리뷰어: @seob"


def check_label(argv):  # P5
    argv = argv or []
    for i, a in enumerate(argv):
        if a in ("--label", "-l"):
            return i + 1 < len(argv) and argv[i + 1].strip() in LABELS
        if a.startswith("--label="):
            return a.split("=", 1)[1].strip() in LABELS
    return False


def check_rollback(t, b):  # P6
    c = _section_content(b, "## 롤백 계획")
    return c is not None and len(c) >= 10


def check_commit_title(subj):  # C1
    if not re.fullmatch(r"\[LAB-123\] " + TYPES + r": .+", (subj or "").strip()):
        return False
    return len(subj.split(":", 1)[1].strip()) >= 2


def check_commit_trailer(body):  # C2
    lines = [ln.strip() for ln in (body or "").splitlines() if ln.strip()]
    return bool(lines) and lines[-1] == "Ref: LAB-123"


def head_commit(repo_dir):
    """initial 이후의 HEAD 커밋 (subject, body). 추가 커밋 없으면 None."""
    try:
        out = subprocess.run(
            ["git", "-C", repo_dir, "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        if int(out.stdout.strip()) < 2:
            return None
        subj = subprocess.run(
            ["git", "-C", repo_dir, "log", "-1", "--format=%s"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        body = subprocess.run(
            ["git", "-C", repo_dir, "log", "-1", "--format=%b"],
            capture_output=True, text=True, check=True,
        ).stdout
        return subj, body
    except (subprocess.CalledProcessError, ValueError, OSError):
        return None


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def fisher_exact_p(k1, n1, k2, n2):
    """2x2 [[k1, n1-k1], [k2, n2-k2]] 양측 Fisher 정확검정 p."""
    total_k, total_n = k1 + k2, n1 + n2

    def prob(x):
        return (
            math.comb(n1, x)
            * math.comb(n2, total_k - x)
            / math.comb(total_n, total_k)
        )

    lo, hi = max(0, total_k - n2), min(total_k, n1)
    p_obs = prob(k1)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p_obs + 1e-12))


PR_RULES = [
    ("P1 제목", check_title),
    ("P2 변경이유", check_reason),
    ("P3 테스트계획", check_test_plan),
    ("P4 리뷰어", check_reviewer),
]
# P5(라벨)는 argv, P6(롤백)은 body — 시그니처가 달라 별도 처리
COMMIT_RULES = [("C1 커밋제목", check_commit_title), ("C2 커밋Ref", check_commit_trailer)]


def grade_run(run_dir):
    label = os.path.basename(run_dir.rstrip("/"))
    captures = sorted(glob.glob(os.path.join(run_dir, "capture", "pr-*.json")))
    pr = None
    if captures:
        with open(captures[-1]) as f:
            pr = json.load(f)
    commit = head_commit(os.path.join(run_dir, "repo"))
    marks = {}
    for name, fn in PR_RULES:
        marks[name] = bool(pr) and fn(pr.get("title"), pr.get("body"))
    marks["P5 라벨"] = bool(pr) and check_label(pr.get("argv"))
    marks["P6 롤백"] = bool(pr) and check_rollback(pr.get("title"), pr.get("body"))
    for name, fn in COMMIT_RULES:
        marks[name] = bool(commit) and fn(commit[0] if name.startswith("C1") else commit[1])
    return {
        "label": label,
        "marks": marks,
        "pr_created": bool(pr),
        "commit_created": bool(commit),
        "all_pass": all(marks.values()),
    }


def main():
    results = []
    for run_dir in sorted(glob.glob(os.path.join(PILOT, "runs", "*"))):
        cond = os.path.basename(run_dir).split("-")[0]
        if cond not in ("AP", "AP12", "ZP"):
            continue
        results.append((cond, grade_run(run_dir)))
    if not results:
        print("채점할 AP/AP12/ZP 런이 없다.")
        return
    names = list(results[0][1]["marks"].keys())
    print(f"{'런':<9} " + " ".join(f"{n:<10}" for n in names) + " PR생성 커밋생성 전부통과")
    totals = {}
    for cond, r in results:
        cells = " ".join(f"{'✅' if r['marks'][n] else '❌':<9}" for n in names)
        print(
            f"{r['label']:<9} {cells} {'✅' if r['pr_created'] else '❌':<5} "
            f"{'✅' if r['commit_created'] else '❌':<7} {'✅' if r['all_pass'] else '❌'}"
        )
        totals.setdefault(cond, []).append(r["all_pass"])
    print()
    for cond, oks in sorted(totals.items()):
        k, n = sum(oks), len(oks)
        lo, hi = wilson_ci(k, n)
        print(f"조건 {cond}: {k}/{n} 전부통과  (Wilson 95% CI: {lo*100:.0f}%–{hi*100:.0f}%)")
    if "AP" in totals and "ZP" in totals:
        ap, zp = totals["AP"], totals["ZP"]
        p = fisher_exact_p(sum(zp), len(zp), sum(ap), len(ap))
        print(f"\nAP vs ZP Fisher 정확검정(양측): p = {p:.4f}")
    print(
        "\n판정은 DESIGN-pressure.md §5의 사전등록 기준을 따른다 "
        "(1차: CI 비겹침, Fisher는 보조지표)."
    )


if __name__ == "__main__":
    main()
