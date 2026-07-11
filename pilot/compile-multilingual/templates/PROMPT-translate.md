# 번역 세션 프롬프트 (Codex, 문서×언어당 새 세션, 격리 디렉터리)

플레이스홀더: `{LANG_NAME}` = Korean | Japanese | Spanish, `{DOC}` = 문서 파일명.

---

Read the single .md document in this directory ({DOC}).

Task: translate it into natural, written {LANG_NAME}. This translation will be
used as benchmark input, so fidelity matters:

- Preserve ALL code, commands, file paths, identifiers, URLs, and inline
  code spans verbatim — never translate or alter anything inside backticks or
  fenced code blocks.
- Translate prose naturally — do not produce word-by-word calques. A native
  {LANG_NAME}-speaking developer should read it as an ordinary engineering
  document.
- Render obligation/prohibition strength with the natural {LANG_NAME}
  equivalent (e.g. "Never ..." must stay an absolute prohibition, "prefer ..."
  must stay a soft preference). Do not strengthen or weaken any requirement.
- Keep the document structure identical: same headings, same tables, same
  lists, same code blocks in the same order.

Write the translation to `{DOC%.md}.{lang}.md` in this directory. Produce only
that file, no commentary. Do not use the network. Do not read anything outside
this directory.
