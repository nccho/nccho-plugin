# nccho-plugin

Personal Claude Code plugin.

## Skills

- **blog-post** — nclovehs.blogspot.com에 올릴 글을 기존 문체(프로그래밍/여행/맛집)에 맞춰 초안으로 작성.
- **team-advisor** — 중요한 의사결정/접근법 비교 요청 시 실험적 agent teams 기능으로 독립적 관점의 팀원을 구성해 자문받고, main agent 자신의 견해와 비교·종합. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 환경변수 필요.
- **daily-report** — 회사 일일 업무보고서를 두괄식·성과중심·서술형 개조식으로 작성하고 `~/.claude/worklog/`의 날짜별 markdown 파일에 누적 보관. 직접 입력/문서 링크/세션 기반 3가지 입력과 작업분야·소요시간 통계 메타데이터 지원.

## Agents

작업 유형에 따라 모델을 라우팅하는 서브에이전트 세트입니다.

- **searcher** (haiku) — 읽기 전용 로컬 조회. git status/log, grep/glob, ls/find/cat 등 상태를 바꾸지 않는 bash 조회.
- **implementer** (sonnet) — 파일 생성/수정, 빌드/테스트/설치 등 side effect가 있는 구현 작업.
- **analyzer** (opus) — 아키텍처 설계, 보안 분석, 접근법 비교 등 심층 추론.

## Hooks

- **session-init.sh** (SessionStart) — 세션 시작 시 위 에이전트 선택 규칙을 컨텍스트에 주입.
- **verify-model.py** (SubagentStart) — 실행되는 서브에이전트의 `model:` 필드가 기대값과 일치하는지 검증하고 `~/.claude/model-routing.log`에 기록.
