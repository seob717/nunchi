# 컴파일 세션 프롬프트 v2 (sonnet 서브에이전트, 셀당 1개)

DESIGN-strength-guidance §2. PROMPT-compile.md와 동일하되 §4만
`commands/compile.md` 개정본(#15 처치)으로 교체. 플레이스홀더: `{DOC_PATH}`, `{DOC_ID}`.
재시도 규칙: JSON 스키마 불일치 시 같은 프롬프트에 "Your previous output
failed schema validation: <오류 1문장>"을 덧붙여 1회 재요청, 두 번째 출력 채택.

---

You are benchmarking a rule-compilation instruction. Read the document at
{DOC_PATH}, then extract rules from it by following the instructions below
exactly (they are §2–§4 of the compiler spec).

## 2. Extract rules
From the document, extract only rules that "are effective when recalled right before a specific action." Criteria:
- Can it be tied to a specific tool call? (creating a PR, committing, editing a specific file, running a specific command)
- General guidance that can't be tied to an action (tone, coding style at large) is **not a compilation target** — skip it and report it at the end as a list of "uncompilable rules."
- **Tables, fenced code blocks, and list items are rule candidates on equal footing with prose.** A constraint doesn't stop being a rule because it sits in a table row or next to a code sample. But distinguish usage catalogs from constraints: a commands table that only lists what you *can* run is documentation, not a rule — it becomes a rule only when the document attaches an obligation, prohibition, or ordering to the action (must / never / before / after / only).
- **One rule per trigger**: when one sentence bundles requirements aimed at *different* triggers ("run X after editing A; run Y before pushing"), split them so each rule carries its own trigger and strength. Do NOT split an enumeration that shares one trigger, one strength, and one source ("run `make format`, `make lint`, `make test` before creating a PR" stays a single rule) — same-trigger copies would deliver the same source document multiple times for nothing.

## 3. Infer triggers
For each rule, set a `tool` (Bash|Edit|Write) and a `pattern` (Python regex). Examples:
- PR rules → tool: Bash, pattern: `gh\s+pr\s+create`
- Commit conventions → tool: Bash, pattern: `git(\s+-\S+(\s+\S+)?)*\s+commit`
- Migration file rules → tool: Edit, pattern: `migrations/`
- Content rules ("no console.log") → tool: Edit, pattern: `console\.log`, field: `new_string`, path: `\.(ts|tsx)$`
A Bash rule's pattern matches against the command string; an Edit/Write rule's pattern matches against the file path. Add `field: <tool_input key>` under `trigger` to match against a specific input field instead (e.g. `new_string` for edit content, `content` for Write). Two hard-won cautions:
- **Content rules must carry a `path:` regex** (ANDed with `pattern` against the file path) scoping them to code files — otherwise the rule fires on example code inside markdown, comments, and even its own source document.
- **Git command patterns must allow global options** — `git\s+commit` misses `git -C <dir> commit`; use the `git(\s+-\S+(\s+\S+)?)*\s+<subcommand>` shape.

## 4. Decide strength
- The default is `require-read` (block once per session with the rule as the reason, let the retry through — guarantees a read at the cost of one retry).
- Actions the document explicitly prohibits get `block`. **Judge by the speech act — advice, obligation, or prohibition — not by surface wording, in whatever language the document is written.** An imperative form can still be advice: "avoid barrel files" recommends, it does not ban. Calibration examples:
  - Prohibition (`block`): "Never …", "Do NOT …" (en) · "절대 …하지 마세요", "…금지" (ko) · "絶対に〜しないでください" (ja) · "NUNCA …", "No uses …" (es)
  - Recommendation (stays `require-read` or `inject`): "avoid …", "prefer …" (en) · "…은 피하세요", "…지양" (ko) · "〜は避けてください" (ja) · "Evita …", "prefiere …" (es)
- Use `inject` for advisory rules where even one blocked attempt is overkill (style reminders, soft conventions): the rule is delivered alongside the tool call with zero friction, but compliance is left to the model's judgment rather than forced by a retry.

Instead of generating rule files (later sections of the spec do not apply here), return the same information as pure JSON. Your final message must be ONLY this JSON object — no markdown fence, no commentary:

{
  "doc": "{DOC_ID}",
  "rules": [
    {"name": "<short-kebab-case-name>", "tool": "Bash|Edit|Write", "pattern": "<python regex>", "field": null, "path": null, "strength": "block|require-read|inject", "evidence": "<short verbatim quote from the document grounding the strength decision>"}
  ],
  "uncompilable": ["one-line summary of each skipped non-action-bindable rule", "..."]
}

`field` and `path` stay null unless the rule needs them per §3. Every regex must compile under Python `re`.
