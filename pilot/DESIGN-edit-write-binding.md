# 사전등록: 파일 내용·구조 룰의 Edit/Write 이중 바인딩 (이슈 #16)

작성 2026-07-12. 이 문서는 실행 전에 커밋으로 동결한다. 실행 중 이탈은 RESULTS
§0에 기록한다.

## 0. 배경과 질문

야생 한국어 측정(`RESULTS-compile-wild-ko.md`, c722690)에서 recall 미스 38건 중
8건이 도구 라벨 축 인공물이었다: 같은 의미의 룰을 gold는 `Write`, 컴파일러는
`Edit`로 바인딩해 same-tool 매칭에서 미스로 계상됐다. 측정 인공물이자 제품
공백이다 — 파일 내용·구조를 제약하는 룰은 수정(Edit)과 생성(Write) 양쪽에
적용되는데, 한쪽에만 바인딩되면 나머지 경로에서 룰이 샌다.

- **Q1 (측정)**: 매칭 기준을 내용·구조 룰에 한해 Edit↔Write 동치로 바꾸면
  도구 라벨 미스 8건이 해소되는가?
- **Q2 (제품)**: `commands/compile.md` §3에 이중 바인딩을 명문화하면 컴파일러가
  내용·구조 룰을 Edit·Write 쌍으로 일관 산출하는가?
- **Q3 (무회귀)**: §3 개정이 recall·과추출·형식을 회귀시키지 않는가?

## 1. 설계 결정 — 컴파일러 쌍 산출 채택, 엔진 동치 기각

이슈 #16 체크박스 2(엔진 쪽 Edit/Write 동치 처리)와의 비교:

| | 컴파일러 쌍 산출 (§3 명문화) | 엔진 동치 처리 |
|---|---|---|
| content 룰 필드 비대칭 | 쌍이 자연 해소 (Edit 쌍둥이 `field: new_string`, Write 쌍둥이 `field: content`) | 단일 룰로 표현 불가 — 도구별 필드 매핑을 룰 스키마·엔진에 신설해야 함 |
| 엔진·스키마 변경 | 없음 | `core/rules.py`·`core/engine.py`·테스트 변경 |
| "one rule per trigger" 정합 | 정합 (도구가 다르면 트리거가 다름) | 원칙에 예외 도입 ("내용 룰에 한해" 조건 분기) |
| 비용 | 룰 파일 수 증가 + always-on 한 줄 요약 중복 | 룰 파일 1개 유지 |

`core/engine.py`의 `_match_field`는 Edit 룰의 content 매칭을 `new_string`,
Write는 `content` 필드로 해야 하므로, "같은 룰"이라도 도구에 따라 매칭 대상
필드가 다르다. 엔진 동치는 이 비대칭을 숨기는 매핑 계층 없이는 성립하지
않는다. **결정: 쌍 산출.** 엔진은 건드리지 않는다.

## 2. 처치 (이 커밋에 포함, 실행 전 동결)

1. `commands/compile.md` §3에 이중 바인딩 원칙 추가 + §5 파일명 규약에
   `-edit`/`-write` 접미사 예시 추가.
2. `pilot/compile-multilingual/templates/PROMPT-compile-v3.md` —
   PROMPT-compile-v2와 동일하되 §3만 개정본으로 교체.
3. `pilot/compile-multilingual/templates/PROMPT-match-wild-v2.md` —
   PROMPT-match-wild와 동일하되 매칭 규칙 1(same tool)에 내용·구조 룰의
   Edit↔Write 동치 예외를 추가하고, `duplicate` 분류에 쌍둥이 예시를 명시.

## 3. 측정 — 두 팔 설계로 기준 효과와 처치 효과 분리

코퍼스·gold는 동결본 그대로: manifest e5bf2b7(4문서, SHA256 검증 후 실행),
gold b204ebb(55룰). 셀 = 문서 4건.

- **컴파일 (처치)**: PROMPT-compile-v3 × sonnet 서브에이전트 셀당 1개(Agent
  tool, general-purpose, 프롬프트 = 치환된 템플릿 본문 그대로) →
  `pilot/compile-wild/outputs-dual/`. 재시도 규칙은 v2와 동일(스키마 불일치 시
  1회).
- **매칭**: Codex(GPT-5) 셀당 새 세션, 격리 디렉터리(문서 + gold.json +
  output.json + PROMPT.md만), 네트워크 금지.
  - **A팔 (기준 효과)**: 동결 `outputs/`(c722690) × PROMPT-match-wild-v2 →
    `pilot/compile-wild/matches-equiv-base/`. 4세션.
  - **B팔 (기준+처치)**: `outputs-dual/` × PROMPT-match-wild-v2 →
    `pilot/compile-wild/matches-equiv-dual/`. 4세션.
- **집계**: `grade_compile_wild.py`(파라미터화 재사용, --outputs-dir/
  --matches-dir로 두 팔 각각). 중복 판정 세션은 두지 않는다(무결성 검사로
  대체 — #13에서 드리프트 0% 확인).

### 지표

- **Q1**: A팔 recall vs 기존 17/55. 기존 도구 라벨 미스 8건의 gold id별 해소
  여부를 전수 표로 수록.
- **Q2**: `outputs-dual/`에서 직접 계수 — Edit∪Write 룰 중 "내용·구조 제약"
  판정 룰의 쌍 산출 비율. 내용·구조 판정은 evidence 문구 기준 수기, 판정표
  전수 수록(행위 자체를 겨냥한 룰 — "커밋된 마이그레이션을 수정하지 마라"류
  — 는 단일 도구가 정답이므로 모수에서 제외).
- **Q3 게이트** (하나라도 실패 시 compile.md §3 개정 커밋 revert):
  - recall: B팔 문서별 recall이 A팔 대비 3건 이상 하락하지 않는다
    (#15 관측 비결정성 대역 ≤2).
  - over-extraction: B팔 0건.
  - 형식(M2): B팔 위반 0건.
- **M5 strength**: 보고만 (게이트 없음 — §4는 이번 처치와 무관, 변동 관찰용).
- evidence 기계 대조(날조 검사)는 B팔에 대해 수행.

### 해석 한계 (사전 명시)

- gold 품질 한계는 #15와 동일하게 승계된다(A1 사람 검수 이탈) — recall 절대값
  이 아니라 A↔B 상대 비교와 쌍 산출 비율이 주요 판독 대상이다.
- 컴파일 비결정성으로 B팔 recall 변동에는 처치 외 잡음이 섞인다. 문서별
  ±2건은 판독하지 않는다.

## 4. 산출물

- `pilot/compile-wild/outputs-dual/*.json`, `matches-equiv-base/*.json`,
  `matches-equiv-dual/*.json` (커밋 — 원장)
- `pilot/RESULTS-edit-write-binding.md`
- 게이트 통과 시: 이슈 #16 체크박스 갱신·종료. 실패 시: §3 revert + 결과 기록.
