---
name: commit-rules
trigger:
  tool: Bash
  pattern: git\s+commit
source: docs/commit-rules.md
strength: require-read
enabled: true
---
커밋 규칙 — 제목 형식, Ref 트레일러.
