#!/usr/bin/env python3
"""nunchi PreToolUse 훅 오버헤드 실측 harness.

Claude Code는 도구 호출마다 `python3 hooks/pretooluse.py`를 서브프로세스로 띄우고
stdin으로 훅 입력 JSON을 넘긴 뒤 stdout을 읽는다. 따라서 사용자가 체감하는
오버헤드는 `decide()` 실행 시간이 아니라 **프로세스 기동 + 임포트 + decide()**
전체다. 이 harness는 실제 엔트리포인트를 동일한 방식으로 호출해 벽시계 시간을 잰다.

측정 조건 (모두 룰 8개 등록 상태 — PROBE-context-economics.md의 8개 문서 구성과 맞춤):

    py-floor   : `python3 -c pass` — 인터프리터 기동 하한선 (nunchi와 무관한 바닥)
    no-rules   : .claude/rules/ 자체가 없음 — 룰 로딩 경로의 하한선
    no-match   : 룰 8개를 파싱하지만 트리거 불일치 — 실사용에서 압도적 다수인 경로
    deliver    : 트리거 일치 첫 발화 — 소스 문서(~10KB)를 읽어 deny 이유로 배달
    redeliver  : 같은 세션 2회차 이후 — 마커 존재로 통과({} 반환)

각 조건은 워밍업 후 N회 반복하고 중앙값·p95를 보고한다. deliver 조건은 매 반복마다
세션 ID를 바꿔 "첫 배달"을 유지한다.

사용법:
    python3 pilot/hook_overhead.py            # N=50 (기본)
    python3 pilot/hook_overhead.py --n 200    # 반복 수 지정
    python3 pilot/hook_overhead.py --json     # 기계 판독용 출력
"""

import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, "hooks", "pretooluse.py")

# 실제 규칙 문서 크기대(PROBE-context-economics.md 기준 문서 8개 ~76KB → 평균 ~9.5KB)
SOURCE_DOC = "# PR 규칙\n\n" + "".join(
    f"{i}. 규칙 항목 {i} — 제목은 [LAB-123] 형식을 따르고 본문에 검증 방법을 적는다.\n"
    for i in range(1, 121)
)

RULE_TMPL = """---
name: rule-{i}
trigger:
  tool: Bash
  pattern: {pattern}
source: docs/rule-{i}.md
strength: require-read
enabled: true
---
요약: 규칙 {i}을 따르라.
"""


def make_project(with_rules=True, n_rules=8):
    """룰 n_rules개가 등록된 임시 프로젝트를 만든다. 마지막 1개만 `gh pr create`에 걸린다."""
    d = tempfile.mkdtemp(prefix="nunchi-overhead-")
    if not with_rules:
        return d
    rules_dir = os.path.join(d, ".claude", "rules")
    docs_dir = os.path.join(d, "docs")
    os.makedirs(rules_dir)
    os.makedirs(docs_dir)
    for i in range(1, n_rules + 1):
        # 마지막 룰만 측정 대상 명령에 매칭시킨다 (나머지 7개는 파싱만 되고 불일치).
        pattern = r"gh\s+pr\s+create" if i == n_rules else rf"never-match-{i}"
        with open(os.path.join(rules_dir, f"rule-{i}.md"), "w") as f:
            f.write(RULE_TMPL.format(i=i, pattern=pattern))
        with open(os.path.join(docs_dir, f"rule-{i}.md"), "w") as f:
            f.write(SOURCE_DOC)
    return d


def run_hook(project_dir, payload):
    """훅을 Claude Code와 동일한 방식으로 1회 호출하고 소요 시간(ms)을 반환한다."""
    env = dict(os.environ, CLAUDE_PROJECT_DIR=project_dir)
    blob = json.dumps(payload).encode()
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, HOOK], input=blob, capture_output=True, env=env, check=False
    )
    elapsed = (time.perf_counter() - t0) * 1000
    # 훅은 어떤 실패에도 exit 0 + 무출력(allow)이 설계다. non-zero면 측정이 아니라
    # 엔트리포인트가 깨진 것이므로 조용히 평균에 섞이게 두지 않는다.
    if proc.returncode != 0:
        raise RuntimeError(
            f"훅이 exit {proc.returncode}로 종료: {proc.stderr.decode()[:200]}"
        )
    return elapsed, proc.stdout.decode()


def py_floor():
    t0 = time.perf_counter()
    subprocess.run([sys.executable, "-c", "pass"], capture_output=True, check=False)
    return (time.perf_counter() - t0) * 1000, ""


def payload(command="gh pr create --title x", session="s1"):
    return {
        "hook_event_name": "PreToolUse",
        "session_id": session,
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


def measure_interleaved(conditions, n, warmup=5):
    """조건들을 라운드로빈으로 번갈아 실행한다.

    조건별로 블록 실행하면 CPU 캐시·thermal·백그라운드 부하 같은 시간 축 효과가
    조건 차이로 오인된다. 매 라운드마다 모든 조건을 한 번씩 돌려 그 효과를
    모든 조건에 균등하게 분산시킨다.
    """
    samples = {label: [] for label, _ in conditions}
    outs = {label: [] for label, _ in conditions}
    for _ in range(warmup):
        for label, fn in conditions:
            fn(0)
    for i in range(n):
        for label, fn in conditions:
            ms, out = fn(i + 1)
            samples[label].append(ms)
            outs[label].append(out)

    results = []
    for label, _ in conditions:
        s = sorted(samples[label])
        results.append(
            {
                "condition": label,
                "n": n,
                "median_ms": round(statistics.median(s), 1),
                "mean_ms": round(statistics.fmean(s), 1),
                "p95_ms": round(s[int(len(s) * 0.95) - 1], 1),
                "min_ms": round(s[0], 1),
                "max_ms": round(s[-1], 1),
                "delivered": sum(1 for o in outs[label] if "permissionDecision" in o),
                "empty_out": sum(1 for o in outs[label] if not o.strip()),
            }
        )
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    d_norules = make_project(with_rules=False)
    d_nomatch = make_project()
    d_deliver = make_project()
    d_re = make_project()
    projects = [d_norules, d_nomatch, d_deliver, d_re]
    try:
        conditions = [
            # nunchi와 무관한 인터프리터 기동 바닥
            ("py-floor", lambda i: py_floor()),
            # 룰 디렉토리 없음
            ("no-rules", lambda i: run_hook(d_norules, payload())),
            # 룰 8개 파싱, 트리거 불일치
            ("no-match", lambda i: run_hook(d_nomatch, payload(command="ls -la"))),
            # 매 반복 새 세션 → 항상 첫 배달(deny + 원본 문서)
            ("deliver", lambda i: run_hook(d_deliver, payload(session=f"deliver-{i}"))),
            # 동일 세션 고정 → 워밍업에서 이미 배달됨, 이후 통과
            ("redeliver", lambda i: run_hook(d_re, payload(session="fixed"))),
        ]
        results = measure_interleaved(conditions, args.n)
    finally:
        for d in projects:
            shutil.rmtree(d, ignore_errors=True)

    env_info = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
    }

    if args.json:
        print(json.dumps({"env": env_info, "results": results}, indent=2))
        return

    print(f"환경: python {env_info['python']} · {env_info['platform']}")
    print(f"      {env_info['machine']} · {env_info['cpu_count']} cores · N={args.n}\n")
    hdr = f"{'조건':<12} {'중앙값':>8} {'평균':>8} {'p95':>8} {'최소':>8} {'최대':>8}  비고"
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        note = ""
        if r["condition"] == "deliver":
            note = f"배달 {r['delivered']}/{r['n']}"
        elif r["condition"] in ("no-match", "redeliver", "no-rules"):
            note = f"무출력 {r['empty_out']}/{r['n']}"
        print(
            f"{r['condition']:<12} {r['median_ms']:>7.1f}ms {r['mean_ms']:>7.1f}ms "
            f"{r['p95_ms']:>7.1f}ms {r['min_ms']:>7.1f}ms {r['max_ms']:>7.1f}ms  {note}"
        )

    floor = next(r for r in results if r["condition"] == "py-floor")["median_ms"]
    print("\nnunchi 순수 기여분 (중앙값 − 인터프리터 기동 바닥):")
    for r in results:
        if r["condition"] == "py-floor":
            continue
        print(f"  {r['condition']:<12} +{r['median_ms'] - floor:.1f}ms")


if __name__ == "__main__":
    main()
