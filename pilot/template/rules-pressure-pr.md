---
name: pr-rules
trigger:
  tool: Bash
  pattern: gh\s+pr\s+create
source: docs/pr-rules.md
strength: require-read
enabled: true
---
PR 생성 규칙 — 제목 형식, 필수 섹션(변경 이유·테스트 계획·롤백 계획), 라벨, 리뷰어 지정.
