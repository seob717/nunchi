---
name: pr-rules
trigger:
  tool: Bash
  pattern: gh\s+pr\s+create
strength: require-read
enabled: true
---
# PR 작성 규칙

1. **제목은 Conventional Commits** (`feat:` / `fix:` / `docs:` / `chore:` …) — release-please가 squash 커밋 제목으로 버전을 산정한다.
2. **본문에 변경 이유와 검증 방법**(테스트·측정 결과)을 적는다. 측정 변경이면 해당 `pilot/RESULTS-*.md`를 링크한다.
3. **corpus 원문·번역본 파일은 절대 포함하지 않는다** — SHA256 ledger만 커밋한다.
