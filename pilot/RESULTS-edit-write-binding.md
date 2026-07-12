# Edit/Write 이중 바인딩 — 결과 (2026-07-12, 이슈 #16)

사전등록: `DESIGN-edit-write-binding.md`(5208f17, 처치 커밋 동일). 코퍼스
manifest e5bf2b7(실행 전 SHA256 재검증 통과), gold b204ebb(55룰) 동결본 그대로.
컴파일 = sonnet 셀당 1개(PROMPT-compile-v3), 매칭 = Codex 새 세션 8건
(A팔 4 + B팔 4, 전부 무결성 통과).

**한 줄 요약**: 매칭 기준의 Edit↔Write 동치화만으로 기존 도구 라벨 미스
6건이 해소됐고(17/55→23/55), §3 개정 후 컴파일러는 내용·구조 룰 15건을
**전부 Edit·Write 쌍으로 산출**(15/15, v1은 3dollars 구조 룰 7건 전부 Edit
단독)했다. 게이트 3종(recall 무회귀·과추출·형식) 통과 — **§3 개정 유지**.

## 0. 실행 기록·이탈

- **B팔 over-extraction 판정 2건 재정(중요)**: 판정자가 3dollars의
  `swiftlint-after-code-edit/-write` 쌍을 over-extraction으로 분류했다. 그러나
  동결 기준의 OE 정의는 "문서의 어떤 실재 룰에도 대응하지 않는 날조·비규칙
  전용"이고, 이 쌍의 evidence("코드 작성 후 반드시 SwiftLint 검증 수행")는
  문서 원문에 실재하며 같은 문장을 겨냥한 gold g4(Bash)도 존재한다 — 실체는
  날조가 아니라 **Bash↔Edit 도구 축 불일치**(v1 출력도 동일하게 Edit 바인딩,
  처치와 무관한 기존 현상). A팔 판정자는 동일 실체를 `gold-miss`로 분류해
  팔 간 분류도 비일관 — 어휘에 "도구 축 불일치" 버킷이 없는 공백이다.
  게이트는 정의 대조로 검증한 날조 건수 0으로 판정하되, 원판정(2)을 그대로
  공개한다. 원장은 판정자 출력 무수정 보존.
- 컴파일 출력 3건(pinpoint, token-monitor, 3dollars-ios)이 JSON 앞 해설
  1문장/펜스 포함 — 스키마 유효, 기계 제거(재시도 0).
- 판정자 자기 표기 비균질(`codex-1.0`/`codex-1`) — 기존 관측과 동일.

## 1. Q1 — 매칭 기준 동치화 효과 (A팔: 동결 outputs × 새 기준)

| doc | 구(#15) | A팔 | 변화 |
|---|---|---|---|
| pinpoint | 2/8 | 2/8 | — |
| dmnote | 2/12 | 2/12 | g2 매치 전환 +1, g10 역전 −1 (판정 비결정성) |
| token-monitor | 5/16 | 5/16 | — |
| 3dollars-ios | 8/19 | 14/19 | Edit↔Write 미스 6건 전부 해소 |
| **합계** | **17/55 (31%)** | **23/55 (42%)** | |

구판정 도구 라벨 미스 7건의 해소 전수: g6·g7·g13·g14·g15·g19(Edit↔Write)
**전부 해소**, g4(Bash↔Edit)는 동치 범위 밖이라 미해소 — 사전 민감도 추정
(24/55)과 정합. 날조 검사: 채점기 플래그 4건 분절 판독 결과 전부 원문 실재
(마크다운 장식 차이), **날조 0**.

## 2. Q2 — 쌍 산출 일관성 (outputs-dual 직접 계수, 판정표 전수)

Edit∪Write 베이스 16개 전수:

| doc | 베이스 | 판정 |
|---|---|---|
| pinpoint | deep-path-import | 쌍 ✓ (내용 룰: Edit=`new_string`/Write=`content` 필드 분화까지 정확) |
| dmnote | agent-plan-before-implementation | 쌍 ✓ (전 파일 계획 선행 룰) |
| token-monitor | package-json-version-sync | Edit 단독 ✓ — "수정 후 sync 스크립트 실행"은 수정 행위 자체를 겨냥, §3의 단일 도구 예외에 해당 |
| 3dollars-ios | swiftlint-after-code / no-direct-xcodeproj / viewmodel-structure / viewcontroller-structure / api-enum-requesttype-structure / repository-protocol-impl-structure / no-registerid-static-property / collectionviewcell-inherit-base / snapkit-leading-trailing / designsystem-only-ui-values / no-then-library / no-swiftui / import-order | 13개 전부 쌍 ✓ |

**이중 적용 대상 15건 중 15건 쌍 산출(100%), 단일 도구가 정답인 1건은 단독
유지** — v1(3dollars 구조 룰 7건 전부 Edit 단독)의 비일관이 사라졌다. content
룰 4쌍(no-registerid, collectionviewcell, snapkit, designsystem, no-then,
no-swiftui, import-order 포함 7쌍)은 field도 `new_string`/`content`로 정확히
분화. B팔 unmatched의 `duplicate` 11건은 매치된 룰의 반대편 쌍둥이 — 설계
그대로다.

## 3. Q3 — 무회귀 게이트 (B팔 vs A팔)

| doc | A팔 | B팔 | 차이 |
|---|---|---|---|
| pinpoint | 2/8 | 3/8 | +1 (g5 qa-pr-before-push 신규 추출) |
| dmnote | 2/12 | 2/12 | — |
| token-monitor | 5/16 | 6/16 | +1 (g4 pr-merge-squash 신규 추출) |
| 3dollars-ios | 14/19 | 12/19 | −2 (g10 스토리보드·g16 네이밍을 uncompilable로 자기신고 — 추출 판단 비결정성) |
| **합계** | **23/55** | **23/55** | |

- **recall 게이트: 통과** — 문서별 하락 최대 −2 (허용 ≤2).
- **과추출 게이트: 통과** — 정의 대조 검증 후 날조 0 (원판정 2건은 §0 재정,
  도구 축 불일치로 실체 확인).
- **형식(M2) 게이트: 통과** — 4문서 43룰 전부 위반 0 (regex 전부 컴파일,
  어휘 위반 0, content 룰 path 스코프 충족).

**판정: §3 개정 유지.**

## 4. M5 strength · evidence (보고만, 게이트 없음)

- A팔 20/23(87%), B팔 20/23(87%) — #15 야생 측정(15/17, 88%)과 같은 수준.
- B팔 불일치 3건: pinpoint require-read→block 2(qa-pr 룰 — "FAIL이면 커밋하지
  마세요"를 금지 화행으로 상향 판단, gold는 require-read), 3dollars
  block→require-read 1(잔존 하향 성향, #15 관측 패턴).
- evidence 기계 대조: B팔 플래그 2건(dmnote) 분절 판독 전부 원문 실재 —
  **날조 0** (A·B 양팔 모두).

## 5. 해석·후속 소재

- 이슈 #16의 두 축이 모두 닫혔다: 측정 인공물은 기준 동치화로(+6), 제품
  공백은 §3 쌍 산출 명문화로(15/15) 해소. 남은 recall 미스는 도구 라벨이
  아니라 추출 판단(자기신고 uncompilable)·gold 스펙 경계 문제다.
- **신규 소재 ①**: "수정 후 X 실행"류 룰의 도구 축 — 컴파일러는 Edit(수정
  시점 배달), gold는 Bash(검증 명령 시점)로 갈린다(g4, 3판 연속 미스).
  배달 철학상 Edit 바인딩이 오히려 유용할 수 있어 매칭 어휘가 아니라 gold
  작성 기준의 문제로 보인다.
- **신규 소재 ②**: unmatched 분류 어휘에 "도구 축 불일치" 버킷이 없어 A팔
  (gold-miss)·B팔(over-extraction)이 같은 실체를 다르게 분류했다 — 다음
  측정 전에 어휘 확장 필요.
- 이중 바인딩의 실사용 비용(룰 파일 수·always-on 한 줄 중복)은 3dollars가
  최대 사례로 룰 13쌍 = 26파일. 지금은 허용 범위로 판단하나, 파일 폭증이
  문제가 되면 엔진의 다중 도구 트리거(`tool: [Edit, Write]` + 도구별 필드
  매핑)를 별도 이슈로 검토.
