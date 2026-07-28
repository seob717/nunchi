# 훅 오버헤드 실측 프로브

실행일: 2026-07-29. harness = `pilot/hook_overhead.py`.
계기: README "How nunchi compares" 절의 `~24ms median per tool call (26ms when a rule
is delivered)` 문장에 재현 가능한 근거 파일이 없었다(커밋 `cdc5667`은 README만 수정).

## 1. 무엇을 재는가

Claude Code는 도구 호출마다 `python3 hooks/pretooluse.py`를 **서브프로세스로** 띄우고
stdin에 훅 입력 JSON을 넘긴 뒤 stdout을 읽는다. 따라서 사용자가 체감하는 지연은
`decide()` 실행 시간이 아니라 **프로세스 기동 + 임포트 + decide()** 전체다.
harness는 실제 엔트리포인트를 동일한 방식으로 호출해 벽시계 시간을 잰다.

조건 (모두 룰 8개 등록 — `PROBE-context-economics.md`의 문서 8개 구성과 맞춤):

| 조건 | 내용 |
|---|---|
| `py-floor` | `python3 -c pass` — 인터프리터 기동 하한선 (nunchi와 무관한 바닥) |
| `no-rules` | `.claude/rules/` 자체가 없음 — 룰 로딩 경로의 하한선 |
| `no-match` | 룰 8개를 파싱하지만 트리거 불일치 — 실사용에서 압도적 다수인 경로 |
| `deliver` | 트리거 일치 첫 발화 — 소스 문서(~10KB)를 읽어 deny 이유로 배달 |
| `redeliver` | 같은 세션 2회차 이후 — 마커 존재로 통과(`{}` 반환) |

**측정 방법 주의**: 조건별 블록 실행은 순서 효과를 조건 차이로 오인하게 만든다.
1차 시도(블록 실행, N=10)에서 `redeliver`가 `deliver`보다 6.8ms 느리게 나왔으나,
라운드로빈 인터리빙으로 바꾸자 그 차이는 사라졌다 — 시간 축 효과였다.
아래 수치는 전부 인터리빙 측정이다.

## 2. 결과

환경: macOS 26.5 · arm64 · 8 cores. `deliver` 전 회차 배달 확인, 나머지 조건 무출력 확인.

| python | N | py-floor | no-rules | no-match | deliver | redeliver |
|---|---|---|---|---|---|---|
| 3.12.11 | 60 | 36.3ms | 58.3ms | 59.1ms | 59.9ms | 59.4ms |
| 3.13.5 | 60 | 36.0ms | 56.3ms | 57.3ms | 58.0ms | 57.3ms |
| 3.14.6 | 100 | 36.8ms | 55.5ms | 56.6ms | 56.3ms | 56.5ms |

(전부 중앙값. p95는 조건별 65~84ms, 최대값은 100~124ms까지 튄다 — 서브프로세스
기동이라 배경 부하에 민감하다.)

**nunchi 순수 기여분** (중앙값 − 같은 실행의 py-floor):

| python | no-rules | no-match | deliver | redeliver |
|---|---|---|---|---|
| 3.12.11 | +22.0ms | +22.8ms | +23.6ms | +23.1ms |
| 3.13.5 | +20.3ms | +21.3ms | +22.0ms | +21.3ms |
| 3.14.6 | +18.7ms | +19.8ms | +19.5ms | +19.7ms |

`decide()` 인프로세스 시간 (프로세스 기동 제외, python 3.14, N=200):
no-match 0.33ms · deliver 0.79ms · redeliver 0.39ms (중앙값).

## 3. 해석

1. **체감 지연은 도구 호출당 중앙값 ~56–60ms**이고, 그중 **~36ms는 파이썬 인터프리터
   기동**이다. nunchi 코드가 아니라 "훅을 서브프로세스로 띄운다"는 구조 자체의 비용이다.
2. **nunchi 순수 기여분은 ~20–24ms** — 대부분이 임포트 비용이다. 실제 판정 로직
   (`decide()`)은 0.3–0.8ms로 무시할 수준이고, 배달이 일어나도 1ms를 넘지 않는다.
3. **배달 여부는 오버헤드에 유의미한 차이를 만들지 않는다.** `no-match`와 `deliver`의
   차이는 세 파이썬 버전 모두에서 1ms 미만이며, 인터리빙 측정의 회차 간 변동
   (p95−중앙값 ≈ 10ms)에 완전히 묻힌다.
4. 파이썬 버전이 올라갈수록 기여분이 줄어든다(3.12 → 3.14에서 −3.5ms) — 임포트가
   지배적이라는 해석과 일관된다.

## 4. README 수정이 필요한 지점

기존 문장: `Hook overhead, measured: ~24ms median per tool call (26ms when a rule is delivered).`

- `~24ms`라는 값 자체는 **nunchi 순수 기여분**으로는 방어된다(3.12에서 23.6ms).
  하지만 `per tool call`은 도구 호출당 총 지연으로 읽히고, 그 값은 **~56–60ms**다.
- `26ms when a rule is delivered` — 배달 시 추가 비용이라는 구분은 **재현되지 않았다.**

제안: 기여분과 총 지연을 분리해 적고, 배달 시 추가 비용 주장은 삭제한다.

> Hook overhead, measured (`pilot/PROBE-hook-overhead.md`): nunchi adds ~20ms per tool
> call on top of the ~36ms Python interpreter startup that any command hook pays —
> ~56ms end to end. The rule-matching logic itself is under 1ms; whether a rule is
> delivered makes no measurable difference.

## 5. 한계

- 단일 머신(macOS arm64, 8 cores) 측정이다. 인터프리터 기동 비용은 OS·디스크·파이썬
  설치 방식(system vs. pyenv vs. uv)에 크게 좌우되므로 절대값은 환경마다 다르다.
  재현하려면 `python3 pilot/hook_overhead.py --n 100`.
- 룰 8개 기준이다. 룰 수가 늘면 파싱 비용이 붙지만, `decide()`가 0.3ms 수준이라
  수십 개까지는 인터프리터 기동에 묻힐 것으로 보인다(미측정).
- Claude Code가 훅 서브프로세스를 실제로 어떤 방식으로 띄우는지(병렬/직렬, 환경 상속)는
  harness가 재현하지 않는다. 여기서 잰 것은 "동일한 입력으로 같은 스크립트를 1회
  실행하는 비용"이다.
