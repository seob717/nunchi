import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.report import summarize

RULE = "---\nname: {n}\ntrigger:\n  tool: Bash\n  pattern: x\n---\nb"


def test_summarize_counts_and_dead_rules():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, ".claude", "rules"))
    for n in ("pr-rules", "dead-rule"):
        with open(os.path.join(d, ".claude", "rules", n + ".md"), "w") as f:
            f.write(RULE.format(n=n))
    log_dir = os.path.join(d, ".claude", "ziptie", "logs")
    os.makedirs(log_dir)
    with open(os.path.join(log_dir, "2026-07-09.jsonl"), "w") as f:
        for dec in ("deny", "allow-after-delivery", "allow-after-delivery"):
            f.write(
                json.dumps(
                    {
                        "ts": "t",
                        "session": "s",
                        "rule": "pr-rules",
                        "tool": "Bash",
                        "decision": dec,
                    }
                )
                + "\n"
            )
    result = summarize(d)
    assert result["rules"]["pr-rules"]["deny"] == 1
    assert result["rules"]["pr-rules"]["allow-after-delivery"] == 2
    assert result["never_triggered"] == ["dead-rule"]


def test_summarize_empty_project():
    d = tempfile.mkdtemp()
    assert summarize(d) == {"rules": {}, "never_triggered": []}


def test_summarize_skips_corrupted_lines():
    d = tempfile.mkdtemp()
    log_dir = os.path.join(d, ".claude", "ziptie", "logs")
    os.makedirs(log_dir)
    with open(os.path.join(log_dir, "2026-07-09.jsonl"), "w") as f:
        f.write("not json\n")
        f.write("null\n")
        f.write("[1, 2]\n")
        f.write(
            json.dumps(
                {
                    "ts": "t",
                    "session": "s",
                    "rule": "pr-rules",
                    "tool": "Bash",
                    "decision": "deny",
                }
            )
            + "\n"
        )
    result = summarize(d)
    assert result["rules"] == {"pr-rules": {"deny": 1}}
