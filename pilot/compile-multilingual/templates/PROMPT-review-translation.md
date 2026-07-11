# 번역 의미 보존 검수 프롬프트 (Codex, 번역 세션과 분리된 새 세션)

DESIGN §2.1. 검수자는 컴파일 출력에 노출되지 않는다. gold 룰 목록은 본다
(룰 단위 보존 판정이 과제이므로). 플레이스홀더: `{LANG_NAME}`.

---

Files in this directory: the English original (.md), its {LANG_NAME}
translation, and gold.json — a frozen list of rules extracted by humans/LLMs
from the ENGLISH original (fields: id, summary, trigger_intent, strength,
evidence).

Task: judge, for EVERY gold rule, whether the translation preserves it. For
each rule check three things against the translated text:

1. meaning — the same requirement exists and says the same thing
2. condition/scope — the same trigger condition and scope (which files,
   which commands, when) survived
3. strength — absolute prohibitions stayed absolute, defaults stayed defaults,
   soft preferences stayed soft

Also check globally: no requirement-like sentence was added or dropped in the
translation that has no counterpart in the original.

Write `review.json` to this directory:

```json
{
  "doc": "<doc id>", "lang": "<ko|ja|es>",
  "reviewer": "llm:codex-<version>(<model>)",
  "verdicts": [
    {"gold_id": "g1", "preserved": true,
     "note": "only if preserved=false: what was lost/changed, quoting the translated passage"}
  ],
  "global_issues": ["requirement-like sentences added/dropped, if any"]
}
```

Every gold id appears exactly once. Be strict — a weakened "Never" or a lost
scope qualifier is preserved=false. Do not use the network. Do not read
anything outside this directory. Produce only review.json.

(For the negative-control document there is no gold.json: instead verify that
the translation introduces or removes no requirement-like sentences, and write
review.json with an empty verdicts array and your findings in global_issues.)
