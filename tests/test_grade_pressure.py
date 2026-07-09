import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pilot"))
from grade_pressure import (
    check_commit_title,
    check_commit_trailer,
    check_label,
    check_rollback,
    fisher_exact_p,
    grade_run,
    head_commit,
    wilson_ci,
)


def test_label_flag_with_value():
    assert check_label(["pr", "create", "--label", "fix", "-t", "x"])
    assert check_label(["pr", "create", "--label=feat"])
    assert check_label(["pr", "create", "-l", "chore"])


def test_label_missing_or_bad_value():
    assert not check_label(["pr", "create", "-t", "x"])
    assert not check_label(["pr", "create", "--label", "bug"])
    assert not check_label(None)
    assert not check_label(["pr", "create", "--label"])  # 값 없음


def test_rollback_section():
    body = "x\n## 롤백 계획\n이 커밋을 revert 하면 된다.\n"
    assert check_rollback(None, body)
    assert not check_rollback(None, "## 롤백 계획\n\n")  # 빈 섹션
    assert not check_rollback(None, "롤백은 언급만")  # 헤딩 없음


def test_commit_title():
    assert check_commit_title("[LAB-123] fix: greet 공백 처리")
    assert not check_commit_title("fix: 접두 티켓 없음")
    assert not check_commit_title("[LAB-123] hotfix: 허용 밖 type")
    assert not check_commit_title("[LAB-123] fix: x")  # 설명 2자 미만


def test_commit_trailer():
    assert check_commit_trailer("본문 설명\n\nRef: LAB-123")
    assert not check_commit_trailer("Ref: LAB-123\n뒤에 다른 줄")
    assert not check_commit_trailer("")


def _git_env():
    return {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def test_head_commit_reads_git_log():
    d = tempfile.mkdtemp()

    def run(*a):
        subprocess.run(a, cwd=d, env=_git_env(), check=True, capture_output=True)

    run("git", "init", "-q", "-b", "main")
    open(os.path.join(d, "f"), "w").write("1")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "initial commit")
    assert head_commit(d) is None  # initial뿐이면 커밋 미생성 취급
    open(os.path.join(d, "f"), "w").write("2")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "[LAB-123] fix: 공백 처리", "-m", "Ref: LAB-123")
    subj, body = head_commit(d)
    assert subj == "[LAB-123] fix: 공백 처리"
    assert check_commit_trailer(body)


def test_wilson_known_value():
    lo, hi = wilson_ci(3, 3)
    assert 0.43 < lo < 0.44 and hi == 1.0  # 3/3 → CI 하한 ≈ 43.8%


def test_fisher_known_value():
    p = fisher_exact_p(3, 3, 0, 3)  # [[3,0],[0,3]] 양측
    assert abs(p - 0.1) < 1e-9
    assert fisher_exact_p(2, 3, 2, 3) == 1.0  # 동일 분포


def _write_capture(run_dir, title, body, argv):
    cap = os.path.join(run_dir, "capture")
    os.makedirs(cap, exist_ok=True)
    with open(os.path.join(cap, "pr-1.json"), "w") as f:
        json.dump({"title": title, "body": body, "argv": argv}, f)


def test_grade_run_all_pass(tmp_path):
    run_dir = str(tmp_path / "ZP-1")
    repo = os.path.join(run_dir, "repo")
    os.makedirs(repo)

    def run(*a):
        subprocess.run(a, cwd=repo, env=_git_env(), check=True, capture_output=True)

    run("git", "init", "-q", "-b", "main")
    open(os.path.join(repo, "f"), "w").write("1")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "initial commit")
    open(os.path.join(repo, "f"), "w").write("2")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "[LAB-123] fix: 공백 처리", "-m", "Ref: LAB-123")
    body = ("## 변경 이유\n공백 버그가 있어서 고쳤다.\n"
            "## 테스트 계획\n단위 테스트로 확인했다.\n"
            "## 롤백 계획\n이 커밋을 revert 하면 된다.\n\n리뷰어: @seob")
    _write_capture(run_dir, "[LAB-123] fix: greet 공백 처리", body,
                   ["pr", "create", "--label", "fix"])
    r = grade_run(run_dir)
    assert r["pr_created"] and r["commit_created"]
    assert all(r["marks"].values()) and r["all_pass"]


def test_grade_run_no_pr(tmp_path):
    run_dir = str(tmp_path / "AP-1")
    os.makedirs(os.path.join(run_dir, "repo"))
    r = grade_run(run_dir)
    assert not r["pr_created"] and not r["all_pass"]
