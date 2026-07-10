# 컴파일 recall 측정 — 사전등록 (2026-07-10)

컴파일 벤치마크(RESULTS-compile-bench.md)는 **추출된** 88룰의 형식 결함 0을 검증했지만,
"문서에 있었는데 컴파일러가 놓친 룰"(recall)은 자기신고 기반 설계라 측정 불가였다
(DESIGN-compile-bench §6에 한계로 명시). 이 실험은 코퍼스 일부에 대해 **사람이 정답
룰셋을 수기 구축**해 그 공백을 메운다. 실행 전에 코퍼스·정답 구축 프로토콜·매칭
규칙·지표를 고정한다. (이슈 #11)

## 1. 질문

- Q1. 문서에 실재하는 액션 결합 가능 룰 중 컴파일러가 추출한 비율은 얼마인가? (recall)
- Q2. 놓친 룰에 패턴이 있는가? — 암시적 표현, 문서 구조(표·코드블록 안), 기타
- Q3. (부차) 정답 대조로 precision을 재검증 — 추출 룰 중 정답에 없는 것은
  "정답 쪽 누락"인가 "과추출"인가?

## 2. 코퍼스 (n=4, 실행 전 고정)

compile-bench 코퍼스(`pilot/compile-bench/manifest.json`의 URL+SHA로 재현) 중
이슈 #11 제안 그대로 밀도 스펙트럼을 커버하는 4건:

| id | 성격 | 선정 근거 |
|---|---|---|
| airflow | 고밀도 (~35KB) | 룰 밀도 최상 — recall이 가장 깨지기 쉬운 조건 |
| nextjs | 고밀도 (~22KB) | 고밀도 2건째 — airflow 단독 관찰의 우연성 방지 |
| supabase | 중간 | PR 체크리스트·마이그레이션 규칙 — 액션 결합 룰 위주 문서 |
| langgraph | 소형 (~1.9KB) | 소형·조건부 규칙 — 정답 전수 작성이 확실히 가능한 하한 |

awm 표집 7건은 제외한다 — 정답 수기 구축 비용 대비 밀도 축 커버리지에 기여가 없다.
코퍼스 파일 비커밋 원칙은 유지한다 (URL+SHA 재현, `corpus/` gitignore).
재수집 시 SHA256이 manifest와 불일치하면 해당 문서를 제외하고 사유를 기록한다.

## 3. 정답 룰셋 구축 프로토콜

- **작성자: 레포 소유자(사람) 1인. LLM은 정답 작성에 관여하지 않는다** — 컴파일러와
  같은 계열 모델이 정답을 쓰면 측정의 독립성이 무너진다. 이 실험에서 에이전트가 해도
  되는 일은 사전등록(이 문서)·집계기·결과 문서 초안까지다.
- 절차: 원문만 열어놓고(컴파일 출력·RESULTS를 옆에 두지 않는다) 문단 단위 전수 통독
  → "액션 결합 가능 룰" 전수 목록 작성. 판정 기준은 `commands/compile.md` §2를 그대로
  사용한다 (특정 도구 호출 시점에 검사 가능한 규칙만).
- 항목당 기록: 요약, tool, 트리거 의도(자연어 — 정규식 작성은 요구하지 않음),
  기대 strength, 원문 인용(evidence).
- 완료 시 `pilot/compile-recall/gold/<id>.json`으로 **커밋해 고정**. 대조(§4)는
  고정 커밋 이후에만 시작한다.

### 3.1 정답 스키마 (`gold/<id>.json`)

```json
{
  "doc": "<id>",
  "author": "human:<github-id>",
  "rules": [
    {"id": "g1", "summary": "...", "tool": "Bash|Edit|Write",
     "trigger_intent": "어떤 액션을 겨냥하는지 자연어로",
     "strength": "block|require-read|inject",
     "evidence": "원문 인용 (짧게)"}
  ]
}
```

## 4. 대조 및 지표

- **대조 대상은 기존 커밋된 `pilot/compile-bench/outputs/<id>.json`이다 (재실행 없음).**
  코퍼스가 SHA로 고정돼 있고 출력이 이미 원장에 커밋돼 있으므로 재실행할 이유가 없고,
  "정답을 보고 컴파일을 다시 돌렸다"는 오염 경로도 원천 차단된다.
- **매칭은 수기**: 정답 룰 ↔ 추출 룰. 판정 기준 — ① tool 일치, ② 트리거가 같은
  액션/콘텐츠를 겨냥(패턴 문자열 동일까지는 요구하지 않음, 의미 동등이면 매치),
  ③ 1:1 매칭(추출 룰 하나가 정답 여럿을 커버하면 가장 근접한 1개만). 부분 크레딧 없음.
  판정 근거는 `matches/<id>.json`에 전부 남긴다.
- 정답 갱신 규칙: 대조 중 "추출 룰이 맞고 정답이 놓쳤다"가 발견되면 정답에 추가할 수
  있다 — **recall 분모가 커지는 방향만 허용**하고, 갱신 이력을 matches 파일의
  `gold_amendments`에 기록한다. 정답에서 룰을 빼는 갱신은 금지.

### 4.1 매칭 기록 스키마 (`matches/<id>.json`)

```json
{
  "doc": "<id>",
  "matches":   [{"gold_id": "g1", "output_rule": "<추출 룰 name>", "rationale": "..."}],
  "misses":    [{"gold_id": "g2", "category": "implicit|structure|reference-depth|other",
                 "note": "..."}],
  "unmatched_extracted": [{"output_rule": "...",
                           "class": "gold-miss|over-extraction|duplicate", "note": "..."}],
  "gold_amendments": [{"gold_id": "g9", "reason": "추출 룰 검토 중 정답 누락 발견"}]
}
```

### 4.2 지표 (집계기 `pilot/grade_compile_recall.py`, stdlib 전용)

- **M1 recall** = `len(matches) / len(gold.rules)` — 문서별 + 전체(마이크로 평균).
- **M2 미스 분류** — misses의 category 분포. Q2의 답.
- **M3 precision 재검** — unmatched_extracted의 class 분포.
  `gold-miss`는 정답 갱신(→ M1 분모 반영)과 함께 기록된다.
- 집계기는 정합성도 검사한다: 정답 룰 전수가 matches∪misses에 정확히 1회씩
  등장하는지, `output_rule`이 실제 outputs 파일에 존재하는지. 위반 시 채점 거부.
  판정은 수기, 집계·검산만 자동.

## 5. 제외 규칙

- 코퍼스 재수집 SHA 불일치 → 해당 문서 제외, 사유 기록 (§2).
- 제외로 n<3이면 실험 중단하고 코퍼스 재설계.

## 6. 해석 한계 (실행 전에 못박음)

- **정답 작성자는 이미 컴파일 출력에 노출됐다** — RESULTS-compile-bench를 쓴 사람과
  동일인이므로 블라인드가 불가능하다. 이 노출은 "출력에 있던 룰이 정답에 들어가기
  쉽다"는 쪽, 즉 **recall을 과대추정하는 방향**으로 작용한다. 결과 보고 시 이 방향성을
  명시하고, 보고되는 recall은 상한 추정으로 해석한다.
- 정답 자체의 완전성(사람이 놓친 룰)은 측정할 수 없다 — recall은 "사람 정답 대비"로만
  해석한다. §4의 갱신 규칙이 이 오차를 줄이지만 없애지는 못한다.
- n=4, 정답 작성자 1인, 매칭 판정자 1인 — 일반화 불가, 파일럿.
- 게이트 없음 — 기술 통계와 미스 패턴 관찰만 보고한다. "recall이 높다/낮다"는
  비교 대상이 없으므로 우열 주장을 하지 않는다.
