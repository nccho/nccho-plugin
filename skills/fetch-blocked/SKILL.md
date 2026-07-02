---
name: fetch-blocked
description: WebFetch로 가져올 수 없는(차단된) 웹페이지에서 데이터를 조회하는 기법입니다. WebFetch가 "Claude Code is unable to fetch" 또는 403을 반환하거나, 네이버·카카오 등 봇 차단이 있는 사이트의 내용을 읽어야 할 때 사용하세요. "이 링크 fetch가 안 돼", "이 사이트 내용 좀 읽어줘(근데 막힘)", "WebFetch가 막힌 페이지" 같은 상황에 적용합니다.
argument-hint: <가져올 URL>
---

# Fetch Blocked Sites

`WebFetch`가 거부하는 페이지(봇 차단, 403, "Claude Code is unable to fetch")에서 데이터를 얻기 위한 폴백 절차. 특정 사이트에 특화된 파싱이 필요하면 별도 스킬(예: `naver-place`)이 이 기법을 사용한다.

## 원칙 (먼저 읽기)

- **개인 용도의 단건 조회에만** 사용한다. 대량·자동 반복 크롤링, 로그인/인증이 필요한 비공개 페이지 우회에는 쓰지 않는다.
- 사이트 `robots.txt`/이용약관을 존중한다. 애매하면 사용자에게 먼저 확인한다.
- **원본 HTML(수십~수백 KB)을 컨텍스트에 붓지 않는다.** 반드시 파일로 저장하고 필요한 필드만 추출한다. 가능하면 추출 자체를 subagent에 위임해 메인 대화를 깨끗하게 유지한다.

## 절차

### 1. 먼저 정상 경로 시도

정상 사이트는 이게 가장 깔끔하다.

```
WebFetch(url, "필요한 정보를 뽑아줘")
```

리다이렉트 안내가 나오면 안내된 URL로 다시 시도한다. 아래 신호가 나오면 2단계 폴백으로 넘어간다.

- `Claude Code is unable to fetch from <domain>`
- HTTP 403 / 봇 차단 페이지

### 2. 브라우저 헤더 curl 폴백

실제 모바일 브라우저처럼 요청한다. **HTML은 stdout이 아니라 파일로** 받는다.

```bash
curl -sL \
  -A "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1" \
  -H "Accept-Language: ko-KR,ko;q=0.9" \
  -o /tmp/fetch-blocked.html \
  -w "HTTP %{http_code}, size %{size_download}\n" \
  "<URL>"
```

- 단축링크(예: `naver.me`)는 `-L`로 리다이렉트를 따라간다. 리다이렉트 경로만 볼 땐 `curl -sIL`로 헤더만 확인한다.
- `/summary`, `/api` 류 내부 엔드포인트는 403이 잦다. 사람이 보는 **모바일 페이지(`m.` 서브도메인 등)**가 대체로 뚫린다.
- 여전히 403이면: 데스크톱 UA로 교체, `Referer`/`Cookie` 추가를 시도하고, 그래도 막히면 사용자에게 "직접 접속해 내용을 붙여달라"고 요청한다.

### 3. 필요한 필드만 추출

받은 파일에서 목표 데이터만 뽑는다. 원본을 그대로 출력하지 않는다.

- 최신 SPA/React 페이지는 데이터가 `window.__APOLLO_STATE__`, `__NEXT_DATA__`, `application/json` 스크립트 블록에 **JSON으로 통째로 박혀 있는** 경우가 많다. 깨지기 쉬운 정규식 나열보다 **그 JSON 블록을 파싱**하는 편이 안정적이다.
- 중괄호 균형으로 JSON 블록을 잘라 `python3`의 `json.loads`로 파싱한 뒤 키로 접근한다.
- 사이트별로 반복 조회한다면, 파싱 로직을 재사용 가능한 스크립트로 만들어 subagent가 실행하게 한다. (예: `naver-place` 스킬의 `scripts/extract_naver_place.py`)

## 마무리

- 무엇을(어떤 필드) 어디서(최종 URL) 가져왔는지, 폴백을 썼는지 한 줄로 보고한다.
- 끝내 실패했으면 정직하게 알리고 대안(수동 붙여넣기)을 제시한다.
