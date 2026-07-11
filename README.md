# nccho-plugin

Personal Claude Code plugin.

설치·사용법은 [INSTALL.md](INSTALL.md) 참고. 빠른 설치:

```
/plugin marketplace add nccho/nccho-plugin
/plugin install nccho-plugin@nccho
```

## Skills

- **goal-interview** — 흐릿한 목표·요구사항을 실제 작업 전에 "참/거짓으로 판정 가능한 완료 기준"으로 바꾸는 역인터뷰. AI가 사용자를 한 번에 하나씩 인터뷰(가정+⚠️ / 엣지 케이스 / 선택지+트레이드오프 / 완료 미리보기)해 기준을 뽑고, 모든 기준이 판정 가능해지면 종료. 반복 기준은 CLAUDE.md로 저축, 위험 단계엔 승인 게이트. 자동 판정 가능한 기준은 내장 `/goal` 커맨드 한 줄(검증 문장 형식 + 비목표 제약 + 턴 백스톱)로 만들어 제안해, 조건 충족까지 자동 실행으로 이어줌.
- **dev-flow** — 코드 수정 요청을 파이프라인(완료 기준 확인 → 브랜치 → 테스트 → 구현 → `/simplify` → `/code-review` → MR 생성 → 승인 대기)으로 진행. 완료 기준이 흐릿하면 `goal-interview`로 시작하고, MR 생성 전 승인 게이트·MR 승인은 사용자 몫으로 고정. main 직접 수정 금지, 단계별 통과 조건 명시.
- **blog-post** — nclovehs.blogspot.com에 올릴 글을 기존 문체(프로그래밍/여행/맛집)에 맞춰 초안으로 작성.
- **team-advisor** — 중요한 의사결정/접근법 비교 요청 시 실험적 agent teams 기능으로 독립적 관점의 팀원을 구성해 자문받고, main agent 자신의 견해와 비교·종합. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 환경변수 필요.
- **daily-report** — 회사 일일 업무보고서를 두괄식·성과중심·서술형 개조식으로 작성하고 `~/.claude/worklog/`의 날짜별 markdown 파일에 누적 보관. 직접 입력/문서 링크/세션 기반 3가지 입력과 작업분야·소요시간 통계 메타데이터 지원.
- **naver-place** — 네이버 지도/플레이스 링크에서 장소 정보(시그니처 메뉴·예약 방법·주차·특색·기본정보)를 뽑아 블로그 맛집 글 소재로 요약. `fetch-blocked` 기법으로 조회하고 추출은 subagent에 위임. `blog-post`로 바로 연계.
- **fetch-blocked** — WebFetch가 차단(403·"unable to fetch")되는 페이지를 브라우저 헤더 curl로 우회 조회하는 공용 기법. 원본 HTML을 컨텍스트에 붓지 않고 필요한 필드만(가능하면 subagent로) 추출.

## Agents

작업 유형에 따라 모델을 라우팅하는 서브에이전트 세트입니다.

- **searcher** (haiku) — 읽기 전용 로컬 조회. git status/log, grep/glob, ls/find/cat 등 상태를 바꾸지 않는 bash 조회.
- **implementer** (sonnet) — 파일 생성/수정, 빌드/테스트/설치 등 side effect가 있는 구현 작업.
- **analyzer** (opus) — 아키텍처 설계, 보안 분석, 접근법 비교 등 심층 추론.

## Hooks

- **session-init.sh** (SessionStart) — 세션 시작 시 위 에이전트 선택 규칙을 컨텍스트에 주입.
- **verify-model.py** (SubagentStart) — 실행되는 서브에이전트의 `model:` 필드가 기대값과 일치하는지 검증하고 `~/.claude/model-routing.log`에 기록.
