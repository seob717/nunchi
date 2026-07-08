#!/usr/bin/env python3
"""JIT 룰 주입 훅 (조건 B 전용).

세션 최초의 `gh pr create` 시도를 한 번 막고, deny 사유에 PR 규칙 전문을 실어
모델에게 전달한다. 같은 세션의 재시도는 통과시킨다 (require-read 강도).
"""

import sys
import json
import os
import re

data = json.load(sys.stdin)
if data.get("tool_name") != "Bash":
    sys.exit(0)
cmd = data.get("tool_input", {}).get("command", "")
if not re.search(r"gh\s+pr\s+create", cmd):
    sys.exit(0)

proj = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
state_dir = os.path.join(proj, ".state")
os.makedirs(state_dir, exist_ok=True)
marker = os.path.join(state_dir, f"seen-{data.get('session_id', 'nosid')}")
if os.path.exists(marker):
    sys.exit(0)  # 이미 규칙을 전달했음 — 통과

with open(marker, "w") as f:
    f.write("1")
with open(os.path.join(proj, "docs", "pr-rules.md")) as f:
    rules = f.read()

reason = (
    "PR 생성 전 점검: 아래 PR 규칙을 빠짐없이 반영한 뒤 다시 gh pr create를 실행해.\n\n"
    + rules
)
print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        ensure_ascii=False,
    )
)
sys.exit(0)
