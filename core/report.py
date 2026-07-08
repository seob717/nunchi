"""ziptie 로그 집계 — 룰별 배달/통과 횟수와 죽은 룰 목록."""
import glob
import json
import os
import sys

from core.rules import load_rules


def summarize(project_dir: str) -> dict:
    counts = {}
    for path in sorted(glob.glob(os.path.join(project_dir, ".claude", "ziptie", "logs", "*.jsonl"))):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                rule_counts = counts.setdefault(entry.get("rule", "?"), {})
                decision = entry.get("decision", "?")
                rule_counts[decision] = rule_counts.get(decision, 0) + 1
    defined = [r.name for r in load_rules(project_dir)]
    return {
        "rules": counts,
        "never_triggered": [n for n in defined if n not in counts],
    }


def main():
    result = summarize(os.getcwd())
    if not result["rules"] and not result["never_triggered"]:
        print("ziptie: 기록된 로그가 없다.")
        return
    print(f"{'룰':<24} {'배달(deny)':<10} {'통과':<6}")
    for name, c in sorted(result["rules"].items()):
        print(f"{name:<24} {c.get('deny', 0):<10} {c.get('allow-after-delivery', 0):<6}")
    for name in result["never_triggered"]:
        print(f"{name:<24} {'한 번도 트리거되지 않음 (죽은 룰?)'}")


if __name__ == "__main__":
    main()
