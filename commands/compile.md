---
description: CLAUDE.md와 참조 문서에서 룰을 추출해 트리거 바인딩 룰 파일로 컴파일한다
argument-hint: "[문서 경로 (생략 시 CLAUDE.md와 그 @참조 전체)]"
---

# /ziptie:compile

다음 절차로 룰을 컴파일해라.

## 1. 입력 수집
- 인자가 있으면 그 문서만, 없으면 프로젝트 CLAUDE.md와 그 안의 `@경로` 참조 문서 전부를 읽는다.

## 2. 룰 추출
각 문서에서 "특정 행동 직전에 상기시켜야 효과 있는 룰"만 추출한다. 판별 기준:
- 특정 도구 호출과 연결 가능한가? (PR 생성, 커밋, 특정 파일 수정, 특정 명령 실행)
- 연결 불가한 일반 지침(톤, 코딩 스타일 전반)은 **컴파일 대상이 아니다** — 건너뛰고 마지막에 "컴파일 불가 룰" 목록으로 보고한다.

## 3. 트리거 추론
룰마다 `tool`(Bash|Edit|Write)과 `pattern`(Python 정규식)을 정한다. 예:
- PR 규칙 → tool: Bash, pattern: `gh\s+pr\s+create`
- 커밋 컨벤션 → tool: Bash, pattern: `git\s+commit`
- 마이그레이션 파일 규칙 → tool: Edit, pattern: `migrations/`
Bash 룰의 pattern은 명령 문자열에, Edit/Write 룰의 pattern은 파일 경로에 매칭된다.

## 4. 강도 결정
- 기본은 `require-read` (세션 최초 1회만 규칙을 배달하고 재시도는 통과).
- 문서가 "절대 금지"라고 명시한 행동만 `block`.

## 5. 룰 파일 생성
룰마다 `.claude/rules/<kebab-case-name>.md`를 만든다. 원본 문서가 있으면 `source`에 프로젝트 상대 경로를 넣고 body에는 한 줄 요약만 쓴다 (배달 시점에 원본을 읽으므로 복붙 금지):

```markdown
---
name: pr-rules
trigger:
  tool: Bash
  pattern: gh\s+pr\s+create
source: docs/pr-rules.md
strength: require-read
enabled: true
---
PR 생성 규칙 — 제목 형식, 필수 섹션, 리뷰어 지정.
```

## 6. 사용자 검토
생성한 룰 파일 목록을 표(이름/트리거/강도/source)로 보여주고, 컴파일 불가 룰 목록과 함께 "수정할 것이 있는지" 물어라. 정규식이 과하게 넓으면 false positive가 되니 보수적으로 좁게 잡는 게 기본값이다.
