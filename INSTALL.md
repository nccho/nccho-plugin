# 설치 & 사용 가이드

nccho-plugin 설치 방법과 사용법. 이 저장소는 이제 마켓플레이스(`.claude-plugin/marketplace.json`)를 포함하므로 GitHub에서 바로 설치할 수 있다.

## 구성

| 종류 | 이름 | 설명 |
|------|------|------|
| Skill | `blog-post` | nclovehs.blogspot.com 문체로 블로그 글 초안 작성 |
| Skill | `team-advisor` | agent teams로 여러 관점 비교 자문 (실험 기능 필요) |
| Skill | `daily-report` | 일일 업무보고서 작성 + `~/.claude/worklog/` 누적 |
| Agent | `searcher` (haiku) | 읽기 전용 로컬 조회 |
| Agent | `implementer` (sonnet) | 파일 생성/수정 등 구현 |
| Agent | `analyzer` (opus) | 아키텍처/보안 심층 분석 |
| Hook | `session-init.sh` | SessionStart: 에이전트 선택 규칙 주입 |
| Hook | `verify-model.py` | SubagentStart: 에이전트-모델 검증·로깅 |

## 설치 방법

### 방법 A. 임시 테스트 (권장 첫 단계)

기존 `~/.claude` 설정을 건드리지 않고 해당 세션에서만 로드한다.

```bash
claude --plugin-dir ~/Repo/nccho-plugin
```

### 방법 B. GitHub에서 정식 설치 (지속적)

Claude Code 안에서 아래 슬래시 명령을 입력한다.

```
/plugin marketplace add nccho/nccho-plugin
/plugin install nccho-plugin@nccho
```

- `nccho/nccho-plugin` : GitHub 저장소 (owner/repo)
- `nccho-plugin@nccho` : `플러그인이름@마켓플레이스이름`

CLI로 확인/관리:

```bash
claude plugin list
claude plugin enable  nccho-plugin@nccho
claude plugin disable nccho-plugin@nccho
```

## ⚠️ 중복 등록 주의

이 플러그인의 `agents/`·`hooks/`와 **동일한 파일이 이미 `~/.claude/agents/`, `~/.claude/hooks/`, `~/.claude/settings.json`에 존재하면** 둘 다 등록된다. 특히 hooks는 이벤트별로 병합되어 **양쪽 모두 실행**되므로 `verify-model.py`가 두 번 돌고 `~/.claude/model-routing.log`에 중복 기록된다.

정식 설치(방법 B) 전에는 기존 `~/.claude`의 중복 agents/hooks와 `settings.json`의 SessionStart/SubagentStart 훅 등록을 제거하는 것을 권장한다. (임시 테스트 방법 A는 무관.)

## 사용법

### Skills

- 문맥에 맞으면 자동 발동하며, 명시 호출도 가능: `/blog-post`, `/daily-report`, `/team-advisor`
- 이름 충돌 시 네임스페이스로 호출: `/nccho-plugin:daily-report`

```
/daily-report 세션 기반으로 오늘 작업 정리해줘
/blog-post 프로그래밍 SSH 키 재설정
```

### Agents

- `/agents`로 설치된 에이전트 목록 확인
- 작업 성격에 따라 서브에이전트로 자동/수동 위임 (읽기 조회→searcher, 구현→implementer, 분석→analyzer)

### Hooks

- 설치 시 SessionStart/SubagentStart 훅이 자동 등록된다.

### team-advisor 활성화 (실험 기능)

`team-advisor`는 Claude Code의 실험적 agent teams 기능이 필요하다. `~/.claude/settings.json`에 환경변수를 추가한다.

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

또는 쉘에서:

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

## 업데이트

### 방법 A(임시 테스트)로 로드한 경우

저장소를 `git pull`로 갱신한 뒤 세션을 재시작한다.

```bash
cd ~/Repo/nccho-plugin && git pull
claude --plugin-dir ~/Repo/nccho-plugin
```

### 방법 B(정식 설치)로 설치한 경우

마켓플레이스를 새로고침한 뒤 플러그인을 업데이트한다. 새로고침만으로는 설치된 플러그인 버전이 갱신되지 않는다.

```
/plugin marketplace update nccho
/plugin update nccho-plugin@nccho
```

- `install`은 이미 설치돼 있으면 거부하므로 업데이트에는 쓸 수 없다. 전용 `update` 명령을 사용한다.
- `update`는 최신 버전으로 교체하며 적용에는 재시작이 필요하다.
