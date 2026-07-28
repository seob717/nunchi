"""pilot/hook_overhead.py harness의 정합성 테스트.

성능 수치 자체는 환경 의존이라 검증하지 않는다. 검증하는 것은
**harness가 측정하고 있다고 주장하는 조건이 실제로 그 조건인지**다.
룰 패턴에 오타가 나면 `deliver` 조건이 조용히 `no-match`가 되어
"배달 비용"이 사실은 불일치 비용이 되는데, 수치만 보면 알 수 없다.
"""

import importlib.util
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.engine import decide  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "hook_overhead",
    os.path.join(os.path.dirname(__file__), "..", "pilot", "hook_overhead.py"),
)
hook_overhead = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(hook_overhead)


def test_make_project_writes_requested_rule_count():
    d = hook_overhead.make_project(n_rules=8)
    try:
        rules = os.listdir(os.path.join(d, ".claude", "rules"))
        docs = os.listdir(os.path.join(d, "docs"))
        assert len(rules) == 8
        assert len(docs) == 8
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_make_project_without_rules_has_no_rules_dir():
    d = hook_overhead.make_project(with_rules=False)
    try:
        assert not os.path.exists(os.path.join(d, ".claude", "rules"))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_deliver_condition_actually_delivers():
    """`deliver` 조건의 페이로드가 실제로 원본 문서 배달을 일으켜야 한다."""
    d = hook_overhead.make_project()
    try:
        out = decide(hook_overhead.payload(session="s1"), d)
        hso = out["hookSpecificOutput"]
        assert hso["permissionDecision"] == "deny"
        # 소스 문서 원문이 이유에 실려야 한다 (배달 비용을 재는 조건이므로)
        assert "규칙 항목 1" in hso["permissionDecisionReason"]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_no_match_condition_actually_does_not_match():
    """`no-match` 조건의 명령은 룰 8개를 파싱하되 어디에도 걸리지 않아야 한다."""
    d = hook_overhead.make_project()
    try:
        assert decide(hook_overhead.payload(command="ls -la", session="s1"), d) == {}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_redeliver_condition_passes_through_after_first():
    """`redeliver` 조건은 같은 세션 고정이므로 2회차부터 통과여야 한다."""
    d = hook_overhead.make_project()
    try:
        first = decide(hook_overhead.payload(session="fixed"), d)
        assert first["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert decide(hook_overhead.payload(session="fixed"), d) == {}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_source_doc_is_realistic_size():
    """소스 문서가 실제 규칙 문서 크기대(~10KB)여야 배달 비용이 대표성을 갖는다."""
    assert 5_000 < len(hook_overhead.SOURCE_DOC.encode()) < 20_000


def test_run_hook_returns_elapsed_and_output():
    """엔트리포인트를 실제로 띄워 시간과 stdout을 돌려주는지 확인한다."""
    d = hook_overhead.make_project()
    try:
        elapsed, out = hook_overhead.run_hook(
            d, hook_overhead.payload(session="probe-1")
        )
        assert elapsed > 0
        assert "permissionDecision" in out
    finally:
        shutil.rmtree(d, ignore_errors=True)
