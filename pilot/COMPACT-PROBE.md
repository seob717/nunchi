# 컴팩션 프리플라이트 프로브 — 결과 기록

pty로 띄운 대화형 `claude` 세션에서 `/compact`를 결정적으로 유발하고, ziptie의
`SessionStart(compact)` 훅(재무장)이 실제로 발화하는지 검증한 기술 스파이크
결과다. 스크립트: `pilot/compact_probe.py`. 실행:

```bash
uv run --with pexpect python3 pilot/compact_probe.py
```

## 결론

**4개 성공 기준 전부 통과.** 독립된 두 번의 실행(147.8s, 167.0s)에서 모두
재현됐다.

## 샌드박스 및 훅 배선

- `pilot/template/repo`를 `pilot/runs/PROBE-1`로 복사 (매 실행마다 새로 생성,
  `pilot/runs/`는 gitignore 대상).
- `pilot/run.sh`의 Z 조건 패턴을 그대로 따름: `settings-A.json`을
  `.claude/settings.json`으로, `rules-pr.md`를 `.claude/rules/pr-rules.md`로
  배치. B 조건 전용 `.claude/hooks/inject.py`는 제거.
- `git init` + 최초 커밋 (git 관련 Bash 허용 규칙이 정상 동작하려면 저장소가
  필요).
- `~/.claude.json`에 샌드박스 경로를 `hasTrustDialogAccepted: true`로 등록
  (run.sh와 동일 — 미등록 시 `.claude/settings.json`이 무시됨).
- **ziptie 훅 배선은 `--plugin-dir`을 사용했다** (run.sh의 Z 조건처럼
  `pretooluse.py`만 수동으로 settings.json에 절대경로로 심는 방식이 아님).
  이유: `hooks/hooks.json`이 PreToolUse와 `SessionStart(matcher: "compact")`를
  둘 다 이미 선언하고 있고 `${CLAUDE_PLUGIN_ROOT}`로 경로를 해석하므로,
  `claude --plugin-dir /Users/yuseobshim/Projects/ziptie`만 넘기면 두 훅이
  자동으로 배선된다. README의 로컬 개발 설치 방법과도 일치한다. run.sh의
  Z 조건은 애초에 SessionStart를 쓸 필요가 없었기 때문에 PreToolUse만
  수동으로 심었을 뿐, `--plugin-dir` 자체를 피할 이유가 있었던 건 아니다.
  탐색 과정에서 `--plugin-dir` 사용 시 추가 신뢰 다이얼로그 없이 곧바로
  두 훅이 정상 동작하는 것을 확인했다.
- 권한: `--dangerously-skip-permissions` 등 우회 플래그는 쓰지 않았다.
  `settings-A.json`의 허용 목록(`Bash(git:*)`, `Bash(gh:*)`, `Bash(ls:*)`,
  `Bash(cat:*)`, `Read`/`Edit`/`Write`/`Glob`/`Grep`)만으로 프로브 시퀀스
  전체가 프롬프트 없이 통과했다.
- gh는 `pilot/mock-bin/gh` (PR 캡처 목)를 `PATH` 최우선에 둬서 사용.

## 시퀀스

1. 초기 렌더링 idle-wait.
2. **룰 트리거**: "Bash 도구로 정확히 다음 명령어를 그대로 실행해(다른
   명령은 실행하지 마): `gh pr create --title "ziptie probe" --body "probe
   body"`" 전송 → ziptie PreToolUse 훅이 `gh\s+pr\s+create` 패턴에 매치해
   deny, `.claude/ziptie/state/<session>--pr-rules` 마커 생성,
   `.claude/ziptie/logs/*.jsonl`에 `"decision": "deny"` 기록.
3. 필러 프롬프트 2개 (파일 요약 요청) — `/compact`가 "대화가 너무 짧다"며
   거부하는 것을 막기 위한 패딩.
4. `/compact` 전송.
5. rearm 로그 엔트리가 나타날 때까지 폴링(최대 90s, 2s 간격) — idle-timeout
   이 너무 이르게 끊기는 경우에 대한 안전장치.
6. **재트리거**: 같은 룰 트리거 메시지를 다시 전송 → 마커가 다시 생성되고
   `deny` 로그가 한 건 더 쌓이면 재배달 성공.
7. `Ctrl-C` 두 번으로 세션 종료, 실패 시 강제 종료(`force=True`).

## 감지 전략

- **응답 완료 감지**: 화면 파싱은 시도하지 않았다. TUI가 스피너 프레임과
  커서 이동 ANSI 시퀀스를 초당 수십 회 뿜어내서 "완료" 신호를 텍스트
  패턴으로 안정적으로 잡기 어려웠다 (탐색 중 `Reticulating…`,
  `Infusing…`, `Hyperspacing…` 등 매 프레임 다른 텍스트가 섞여 나옴을
  확인). 대신 `read_nonblocking`으로 계속 드레인하면서 마지막 바이트
  수신 이후 idle(기본 4~5초) 동안 새 데이터가 없으면 "응답 완료"로
  판정했다.
- **최종 판정은 항상 디스크 그라운드 트루스**: state 마커 파일 존재 여부와
  `.claude/ziptie/logs/*.jsonl`의 `decision` 필드로 각 단계 성공 여부를
  검증했다. idle-timeout은 "다음 입력을 보내도 되는 시점"을 잡는 용도로만
  쓰고, 실제 합격/불합격 판정에는 관여하지 않는다.
- **확인창(confirmation dialog) 자동 처리**: 탐색 중, 모델이 재시도 시 PR
  본문에 개행이 포함된 다중 섹션(`## 변경 이유` 등)을 넣으면 Claude Code
  자체 안전장치가 "Newline followed by # inside a quoted argument can hide
  arguments from path validation — Do you want to proceed?"라는 확인창을
  띄우는 것을 발견했다 (ziptie와 무관한 Claude Code 내장 휴리스틱). 최종
  스크립트는 누적 버홈퍼에서 `Do you want to proceed`를 정규식으로 감지하면
  Enter(기본 선택지 "1. Yes")를 자동 전송하도록 만들었다. ANSI 코드는
  단어 *사이*에 커서 이동 시퀀스로 끼어들 뿐 단어 내부를 쪼개지 않아서,
  이스케이프 시퀀스를 제거한 버퍼에서 부분 문자열 매치만으로 충분히
  신뢰할 수 있었다.
- **텍스트 전송/제출 분리**: `child.send(text + "\r")`처럼 한 번에 보내면
  TUI가 이를 붙여넣기로 인식해 제출되지 않는 현상을 탐색 중 재현했다
  (문자열이 입력창에 그대로 남아있고 응답이 시작되지 않음). 최종 스크립트는
  텍스트를 먼저 보내고 0.5초 대기한 뒤 `\r`을 별도로 전송한다.

## 기준별 확인 내역

| # | 기준 | 결과 | 근거 |
|---|---|---|---|
| 1 | pty 세션에 프롬프트를 보내고 응답 완료를 감지 | **PASS** | idle-timeout 기반 감지로 매 턴(트리거, 필러 2개, `/compact`, 재트리거) 정상적으로 완료 시점을 포착. 실행 1: turn1 46.2s / 실행 2: turn1 33.3s. |
| 2 | `/compact` 전송 시 실제 컴팩션 발생 | **PASS** | `rearm`은 `hooks/sessionstart.py`가 `input_data["source"] == "compact"`일 때만(SessionStart 훅의 `matcher: "compact"`) 호출되므로, 로그에 `"decision": "rearm"` 엔트리가 남았다는 것 자체가 실제 컴팩션이 일어났다는 간접(그러나 강한) 증거다. `/compact` 처리에 실행 1: 55.2s, 실행 2: 56.0s 소요. |
| 3 | 컴팩션 직후 SessionStart(compact) 훅 발화 → 마커 제거 + JSONL `rearm` | **PASS** | 두 실행 모두 `.claude/ziptie/logs/*.jsonl`에 `{"decision": "rearm", "count": 1, ...}` 기록, 동시에 컴팩션 전 존재하던 `<session>--pr-rules` state 마커가 컴팩션 후 사라짐(re-listing state dir로 확인). session_id는 컴팩션 전후로 동일하게 유지됨을 확인 (rearm의 `session` 필드가 이전 `deny` 엔트리와 동일). |
| 4 | 스크립트 1회 실행으로 무인 재현 | **PASS** | 사람 개입 없이 `uv run --with pexpect python3 pilot/compact_probe.py` 한 줄로 ①~⑤ 전 시퀀스가 끝까지 자동 진행되고 종료 코드 0으로 마무리됨. 확인창 자동 응답까지 포함해 무인 실행. 독립된 두 번의 실행으로 재현성 확인 (총 소요 147.8s, 167.0s). |

보너스로 검증된 것 (성공 기준에는 없지만 강한 추가 증거): 재트리거 이후
`deny` → (재시도) `allow-after-delivery` 흐름까지 정상 관찰된 실행도 있었다
(마커가 존재하면 같은 세션의 재시도를 통과시키는 `require-read` 강도의
설계 의도가 컴팩션 이후에도 그대로 유지됨을 보여준다).

## 러프한 소요 시간 (실행 2회 평균)

| 구간 | 소요 |
|---|---|
| 초기 렌더링 | ~5–15s |
| 턴 1 (룰 트리거, deny까지) | ~33–46s |
| 필러 턴 2개 | ~15–40s 각 |
| `/compact` (deny→rearm 로그까지) | ~55–56s |
| 재트리거 | ~10–15s |
| **전체 스크립트 실행** | **~148–167s** |

## 사용한 모델 / 환경 메모

- 별도로 `--model`을 지정하지 않아 계정 기본 모델("Fable 5"로 표기됨,
  본 환경의 별칭)로 실행됐다. 성공 기준은 모델 선택과 무관하다.
- `⚠ 1 MCP server needs authentication · run /mcp` 배너가 매 실행 초반에
  뜨지만 확인창이 아니라 상태 표시줄이라 프로브 진행에 영향 없음.
- transcript 원본은 `pilot/runs/PROBE-1-transcript.log`에 남지만
  `pilot/runs/`는 gitignore 대상이라 커밋되지 않는다 (재현 시 자동 재생성).

## 후속 작업(Task 4)에 대한 메모

- `--plugin-dir` 방식이 `SessionStart(compact)`까지 포함해 안정적으로
  동작함을 확인했으므로, `pilot/run.sh`에 컴팩션 관련 조건을 추가할 때도
  같은 방식을 재사용할 수 있다 (수동 settings.json 훅 패치보다 코드가
  간단하고, hooks.json 스펙 변경에 자동으로 따라간다).
- `/compact` 왕복에 ~55초가 걸리므로, 이 흐름을 배치로 여러 번 돌리는
  설계라면 시간 예산에 반영해야 한다.
