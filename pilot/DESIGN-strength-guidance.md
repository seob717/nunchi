# strength 판정 지침 보강 — M5 전후 비교 (이슈 #15, 사전등록)

이 문서는 실행 전에 커밋으로 동결한다. 실행 중 이 문서와 템플릿은 수정하지 않으며,
불가피한 이탈은 RESULTS §0에 기록한다.

## 1. 처치 (treatment)

`commands/compile.md` §4를 이 커밋에서 다음과 같이 개정한 것이 처치의 전부다:

- block 기준을 "absolutely forbidden 표기"에서 **명시적 금지 화행**으로 재정의.
- **화행(권고/의무/금지)으로 판정, 표층 단어·언어 불문** 원칙 명문화.
- 언어별 보정 예시 추가 — 금지: "Never/Do NOT"(en)·"절대 …하지 마세요/금지"(ko)·
  "絶対に〜しないでください"(ja)·"NUNCA/No uses"(es), 권고: "avoid/prefer"(en)·
  "피하세요/지양"(ko)·"〜は避けてください"(ja)·"Evita/prefiere"(es).

근거는 #13 실측 3건(이슈 #15 본문): ko "avoid" 번역의 금지 오독 2회, ja "絶対に"
강화가 만든 유일한 block 일치, 전 언어 공통 block→require-read 하향.

## 2. 프로토콜 — #13(DESIGN-compile-multilingual.md, da4dd51)과 동일, 차이만 명시

- **셀**: 동일 15셀(4문서 × en/ko/ja/es − supabase.ko). supabase.ko는 #13에서
  번역 실패(ITT) — 번역 단계는 처치와 무관하므로 재시도하지 않고 실패 셀 유지.
- **번역본**: #13 동결본 그대로 재사용. 실행 전 12건 전부
  `compile-multilingual/translation-shas.txt` SHA256 재검증 완료.
- **컴파일**: sonnet 서브에이전트 셀당 1개, 같은 배치. 프롬프트는
  `templates/PROMPT-compile-v2.md`(§4만 개정본으로 교체, 나머지 문구 동일).
- **매칭**: Codex 새 세션 11셀(규칙 문서 3종), `templates/PROMPT-match.md` 동일본.
  gold = 93da52e 동결(gold_amendments 비허용). **중복 판정은 생략** — #13에서
  드리프트 0% 실측에 의존한다(이 생략은 사전 결정이며 한계로 기록).
- **저장**: `compile-multilingual/outputs-v2/`, `matches-v2/`. 집계는
  `grade_compile_multilingual.py --outputs-dir … --matches-dir …` 재사용.

## 3. 지표·판정 규칙

- **주지표 M5**: gold 기대 strength 대비 매치 룰의 일치율·confusion. 전(=#13
  RESULTS §5) 대비 후를 셀별로 비교한다. 문서당 1런이므로 개선의 통계적 주장은
  하지 않는다 — 방향과 크기를 보고한다.
- **게이트 1 (M1 recall)**: 셀별 matches 수가 #13 대비 **3룰 초과 하락하면 실패**
  (허용 폭 3룰 = #13에서 관측한 언어 간·런 간 변동 범위).
- **게이트 2 (M4 over-extraction)**: 판정 셀 전부 0 유지. 1건이라도 나오면 실패.
- **게이트 3 (M2 형식)**: 위반 0 유지.
- microfolio(음성 대조군) 룰 수는 보고만 한다 — #13에서 런간 비결정성이 언어
  효과보다 컸으므로 게이트로 삼지 않는다.
- **판정**: 게이트 전부 통과 → §4 개정 유지. 하나라도 실패 → 개정 revert 커밋 후
  실패 내용을 #15에 기록.

## 4. 산출물

`RESULTS-strength-guidance.md` — §0 실행 기록·이탈, M5 전후 표, 게이트 판정,
해석·한계. 코퍼스·번역본은 비커밋 원칙 유지(SHA 원장만).
