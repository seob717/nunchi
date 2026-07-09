import glob
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.engine import decide

RULE = """---
name: pr-rules
trigger:
  tool: Bash
  pattern: gh\\s+pr\\s+create
source: docs/pr-rules.md
strength: require-read
---
요약: PR 규칙을 따르라.
"""


def make_project(rule_text=RULE, with_source=True):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, ".claude", "rules"))
    with open(os.path.join(d, ".claude", "rules", "pr.md"), "w") as f:
        f.write(rule_text)
    if with_source:
        os.makedirs(os.path.join(d, "docs"))
        with open(os.path.join(d, "docs", "pr-rules.md"), "w") as f:
            f.write("# PR 규칙\n1. 제목은 [LAB-123] 형식")
    return d


def hook_input(command="gh pr create --title x", session="s1", tool="Bash"):
    return {
        "hook_event_name": "PreToolUse",
        "session_id": session,
        "tool_name": tool,
        "tool_input": {"command": command},
    }


def test_first_match_denies_with_source_content():
    d = make_project()
    out = decide(hook_input(), d)
    hso = out["hookSpecificOutput"]
    assert hso["permissionDecision"] == "deny"
    assert "[LAB-123]" in hso["permissionDecisionReason"]  # 원본 문서가 배달됨
    assert "ziptie" in hso["permissionDecisionReason"]


def test_second_call_same_session_allows():
    d = make_project()
    decide(hook_input(session="s2"), d)
    assert decide(hook_input(session="s2"), d) == {}


def test_different_session_denies_again():
    d = make_project()
    decide(hook_input(session="s3"), d)
    assert (
        decide(hook_input(session="s4"), d)["hookSpecificOutput"]["permissionDecision"]
        == "deny"
    )


def test_no_match_allows():
    d = make_project()
    assert decide(hook_input(command="git status"), d) == {}
    assert decide(hook_input(tool="Read"), d) == {}


def test_block_strength_always_denies():
    d = make_project(RULE.replace("strength: require-read", "strength: block"))
    decide(hook_input(session="s5"), d)
    out = decide(hook_input(session="s5"), d)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_missing_source_falls_back_to_body():
    d = make_project(with_source=False)
    reason = decide(hook_input(), d)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "PR 규칙을 따르라" in reason


def test_file_tool_matches_on_file_path():
    rule = "---\nname: test-rules\ntrigger:\n  tool: Edit\n  pattern: \\.test\\.\n---\n테스트 규칙 본문"
    d = make_project(rule, with_source=False)
    inp = {
        "hook_event_name": "PreToolUse",
        "session_id": "s6",
        "tool_name": "Edit",
        "tool_input": {"file_path": "src/a.test.ts", "new_string": "x"},
    }
    assert decide(inp, d)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_logs_written():
    d = make_project()
    decide(hook_input(session="s7"), d)
    logs = glob.glob(os.path.join(d, ".claude", "ziptie", "logs", "*.jsonl"))
    assert logs
    entry = json.loads(open(logs[0]).readline())
    assert entry["rule"] == "pr-rules" and entry["decision"] == "deny"


def test_engine_never_raises_on_garbage_input():
    d = make_project()
    assert decide({}, d) == {}
    assert decide({"tool_name": "Bash"}, d) == {}


def test_multiple_require_read_rules_merge_in_single_deny():
    d = make_project()
    rule2 = RULE.replace("name: pr-rules", "name: pr-rules-2").replace(
        "docs/pr-rules.md", "docs/pr-rules-2.md"
    )
    with open(os.path.join(d, ".claude", "rules", "pr2.md"), "w") as f:
        f.write(rule2)
    with open(os.path.join(d, "docs", "pr-rules-2.md"), "w") as f:
        f.write("# PR 규칙2\n2. 두번째 규칙 내용")

    out = decide(hook_input(session="s10"), d)
    hso = out["hookSpecificOutput"]
    assert hso["permissionDecision"] == "deny"
    reason = hso["permissionDecisionReason"]
    assert "[LAB-123]" in reason
    assert "두번째 규칙 내용" in reason
    assert "pr-rules" in reason and "pr-rules-2" in reason
    assert "\n\n---\n\n" in reason

    state_dir = os.path.join(d, ".claude", "ziptie", "state")
    assert os.path.exists(os.path.join(state_dir, "s10--pr-rules"))
    assert os.path.exists(os.path.join(state_dir, "s10--pr-rules-2"))

    assert decide(hook_input(session="s10"), d) == {}


def test_block_and_require_read_mixed_second_call_denies_with_block_only():
    d = make_project()
    block_rule = RULE.replace("name: pr-rules", "name: pr-block")
    block_rule = block_rule.replace("strength: require-read", "strength: block")
    block_rule = block_rule.replace("docs/pr-rules.md", "docs/pr-block.md")
    with open(os.path.join(d, ".claude", "rules", "pr-block.md"), "w") as f:
        f.write(block_rule)
    with open(os.path.join(d, "docs", "pr-block.md"), "w") as f:
        f.write("# 차단 규칙\n절대 금지")

    first = decide(hook_input(session="s11"), d)
    reason1 = first["hookSpecificOutput"]["permissionDecisionReason"]
    assert "pr-rules" in reason1 and "pr-block" in reason1

    second = decide(hook_input(session="s11"), d)
    assert second["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason2 = second["hookSpecificOutput"]["permissionDecisionReason"]
    assert "pr-block" in reason2
    assert "pr-rules" not in reason2


def test_bad_encoding_source_does_not_void_batch():
    d = make_project()
    rule2 = RULE.replace("name: pr-rules", "name: pr-rules-2").replace(
        "docs/pr-rules.md", "docs/pr-rules-2.md"
    )
    with open(os.path.join(d, ".claude", "rules", "pr2.md"), "w") as f:
        f.write(rule2)
    with open(os.path.join(d, "docs", "pr-rules-2.md"), "wb") as f:
        f.write(b"\xff\xfe broken content")  # 잘못된 UTF-8

    out = decide(hook_input(session="s30"), d)
    hso = out["hookSpecificOutput"]
    assert hso["permissionDecision"] == "deny"
    reason = hso["permissionDecisionReason"]
    assert "[LAB-123]" in reason  # rule1 콘텐츠는 정상 배달
    assert "pr-rules-2" in reason  # rule2도 (폴백이든 스킵이든) 배치에서 사라지지 않음

    state_dir = os.path.join(d, ".claude", "ziptie", "state")
    assert os.path.exists(os.path.join(state_dir, "s30--pr-rules"))

    # 두번째 호출에서 배달되지 않은 룰이 조용히 allow되면 안 된다.
    # rule1은 이미 배달됐으니 allow, rule2가 실제로 배달됐다면 그것도 allow.
    second = decide(hook_input(session="s30"), d)
    assert second == {}


def test_broken_rule_warning_once_per_session(capsys):
    broken = "---\nname: a/b\ntrigger:\n  tool: Bash\n  pattern: foo\n---\nbody"
    d = make_project()
    with open(os.path.join(d, ".claude", "rules", "aa-broken.md"), "w") as f:
        f.write(broken)
    capsys.readouterr()  # 이전 출력 비우기

    decide(hook_input(session="s9"), d)
    first_err = capsys.readouterr().err
    assert "invalid name" in first_err

    decide(hook_input(session="s9"), d)
    second_err = capsys.readouterr().err
    assert second_err == ""

    marker = os.path.join(d, ".claude", "ziptie", "state", "warned--s9")
    assert os.path.exists(marker)


def test_bad_regex_warning_once_per_session(capsys):
    broken = (
        "---\nname: broken-re\ntrigger:\n  tool: Bash\n  pattern: (unbalanced\n---\nb"
    )
    d = make_project()
    with open(os.path.join(d, ".claude", "rules", "aa-broken.md"), "w") as f:
        f.write(broken)  # 정렬상 pr.md보다 먼저 로드되도록 aa- 접두
    capsys.readouterr()  # 이전 출력 비우기

    decide(hook_input(session="s21"), d)
    first_err = capsys.readouterr().err
    assert "match error" in first_err

    decide(hook_input(session="s21"), d)
    second_err = capsys.readouterr().err
    assert second_err == ""


def test_broken_regex_rule_does_not_disable_others():
    broken = (
        "---\nname: broken-re\ntrigger:\n  tool: Bash\n  pattern: (unbalanced\n---\nb"
    )
    d = make_project()
    with open(os.path.join(d, ".claude", "rules", "aa-broken.md"), "w") as f:
        f.write(broken)  # 정렬상 pr.md보다 먼저 로드되도록 aa- 접두
    out = decide(hook_input(session="s8"), d)
    assert (
        out["hookSpecificOutput"]["permissionDecision"] == "deny"
    )  # pr-rules는 여전히 발동
