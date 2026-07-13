---
name: issue-rules
trigger:
  tool: Bash
  pattern: gh\s+issue\s+create
strength: require-read
enabled: true
---
# 이슈 작성 규칙

1. **제목**: `영역: 문제 요약` — 영역은 compile / engine / docs / 실험 등. 해결책이 아니라 문제를 요약한다.
2. **본문에 `## 문제` 섹션 필수** — 실측 근거가 있으면 `pilot/` 결과 파일 경로와 커밋 해시를 링크한다.
3. **작업 항목은 `## 제안` 섹션에 체크박스**(`- [ ]`)로 나열한다.
4. **측정이 걸린 변경이면 게이트(무회귀 조건)를 본문에 명시한다** — recall·과추출·포맷 등.
