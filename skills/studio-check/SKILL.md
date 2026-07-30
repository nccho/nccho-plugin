---
name: studio-check
description: Roblox Studio 개발 루프의 연결·동기화·리그 상태를 점검하고 고칩니다. "코드를 고쳤는데 인게임이 안 바뀐다", "Studio 연결 확인해줘", "몹이 안 걷는다/공중에 뜬다", "Play 검증 전에 환경부터 봐줘" 같은 상황, 또는 Studio 작업을 시작하기 전 워밍업으로 사용하세요. Roblox MCP(execute_luau/start_stop_play)와 rojo를 쓰는 프로젝트 전용입니다. 게임 로직 자체를 디버깅하는 스킬은 아닙니다(환경·리그 계층 전용).
argument-hint: [점검 범위 (예: 연결만 / 리그만 / 전체)]
---

# Studio Check

Roblox 개발 루프가 **"고쳤는데 안 바뀐다"** 상태에 빠졌을 때, 어느 계층이 끊겼는지
위에서부터 좁혀 찾아 고친다. 그리고 Play 검증 전에 리그·피직스가 건강한지 확인한다.

핵심 원칙 두 가지 — 이 스킬의 존재 이유다.

- **"프로세스가 살아 있음" ≠ "응답함".** 프로세스 목록과 포트 LISTEN이 둘 다 정상인데
  서버가 죽어 있는 경우를 실제로 겪었다. 반드시 **엔드포인트를 찔러서** 판정한다.
- **음성(negative) 결과가 나오면 계측기부터 의심한다.** "안 움직인다"는 결과의 대부분은
  대상이 고장난 게 아니라 **틀린 것을 재고 있었기** 때문이다(§4).

## 1. 연결 3층 — 위층부터 순서대로

세 계층이 **독립적으로** 죽는다. 하나가 살아 있다고 다른 게 살아 있다는 뜻이 아니다.

| 층 | 무엇 | 살아있는지 판별 | 죽었을 때 |
| --- | --- | --- | --- |
| A | MCP 채널 (Claude↔Studio) | `get_studio_state`가 모드를 반환 | §1-A |
| B | rojo serve (디스크↔네트워크) | `/api/rojo`가 **200** | §1-B |
| C | rojo 플러그인 (네트워크↔Studio) | 디스크와 Studio의 **소스 길이 일치**(§2) | §1-C |

프로젝트에 `scripts/studio-preflight.sh`가 있으면 **먼저 그것부터 돌린다** — B와 플러그인
사망 로그를 MCP 없이 판정한다. **C는 셸로 판정 불가**(아래 경고) → 표대로 확인한다.

⚠️ **`netstat`의 ESTABLISHED를 C의 근거로 쓰지 말 것.** Rojo 패널 Disconnect 후에도
Studio는 `:34872` 소켓을 계속 물고 있고, 그 상태에서 동기화는 죽어 있다(2026-07-30 실측:
링크 1개 · 새 파일 미도달). **가짜 ✅는 없느니만 못하다**(§4).

### 1-A. MCP 채널

**첫 호출은 `list_roblox_studios` → `set_active_studio`다.** active studio가 미설정이면
("a heuristic will be used" 경고) `screen_capture`가 타임아웃한다 — 2026-07-30에 원인
확정·해소. 설정 후에는 **Edit·Play 양쪽에서 캡처가 된다**(도구 설명의 "edit-time"에
속아 "Play 중엔 캡처 불가"로 결론 내지 말 것).

`get_studio_state` 호출. 실패 유형별 대응:

- **"tools fetch failed / timed out"** → 죽은 세션이 남긴 **좀비 프록시**가 원인인 적이
  있다. `mcp.bat`을 물고 있는 오래된 프로세스를 찾아 종료한 뒤 재연결한다.

  ```bash
  powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'mcp.bat' } | Select-Object ProcessId, CreationDate"
  ```

  세션 시작 시각보다 확연히 오래된 것만 `taskkill //F //PID <id>`.
- **"Unable to find an active Studio instance"** → Studio에서 MCP 플러그인 토글이 꺼져
  있다. 유저에게 켜달라고 요청(내가 못 켠다).
- 그래도 안 되면 `mcp.bat`의 경로가 깨졌을 수 있다(과거 하드코딩 경로 사망 전례).

### 1-B. rojo serve

```bash
curl -s -m 5 -o /dev/null -w "%{http_code}\n" http://localhost:34872/api/rojo
```

**200이 아니면 죽은 것.** `000`이면 연결 실패다. 프로세스·포트만 보고 "살아 있다"고
판정하지 말 것 — 실제로 그렇게 오진했다.

죽었으면 **유저 본인 터미널에서** 띄워달라고 요청한다. Claude 세션 배경으로 띄우면
세션과 함께 죽는다.

```bash
cd <프로젝트> && rojo serve
```

### 1-C. rojo 플러그인 연결

serve는 200인데 §2의 소스 길이가 다르면 플러그인이 끊긴 것이다. 유저에게 Rojo 패널
→ **Connect** 요청. 원인은 둘 중 하나이고, **원인마다 조치가 다르다.**

**(a) 플러그인이 죽었다 — Studio 가동 10~15시간마다.** Studio 로그에 남는다:

```bash
ls -t "$LOCALAPPDATA/Roblox/logs"/*_Studio_*.log | head -1 | xargs grep -c "stack overflow"
```

`C stack overflow ... Rojo.Packages.Promise`가 잡히면 그 시각 이후 동기화는 죽어 있었다
(2026-07-24~30 사이 7회 관측: 가동 9.7·10.4·20.2·23.2·43.6·80·93시간). **`serve`는 그동안
200을 계속 반환**하므로 서버만 보면 정상으로 보인다 — 이게 이 실패가 조용한 이유다.
Rojo 7.7.0 체인지로그에 해당 수정 없음 → 실질적 예방은 **Studio를 며칠씩 켜두지 않는 것**.
가동 8시간을 넘겼고 긴 검증이 예정돼 있으면 **먼저 Studio 재시작을 권한다.**

**(b) 재연결은 됐는데 확인 모달에서 멈췄다.** `Confirmation Behavior`가 `Initial`이고
변경이 `Large Changes Threshold`(기본 5)를 넘으면, 연결 후 **유저가 Accept를 누를 때까지**
동기화가 대기한다. 자동 재연결이 성공했는데도 화면은 옛 코드다. 반복 작업이면 Rojo 패널
→ Settings → **Confirmation Behavior = `Never`**를 권한다.

⚠️ **`Auto Reconnect` / `Auto Connect Playtest Server`는 예방책이 아니다.** 이 스킬의
이전 판이 "켜라"고 안내했지만, 2026-07-30 실측에서 **둘 다 이미 ON인 채로 계속 끊기고
있었다**. 켜져 있는지는 확인하되(설정 실물 = `%LOCALAPPDATA%\Roblox\<userId>\
InstalledPlugins\0\settings.json`의 `Rojo_*` 키), 거기서 진단을 멈추지 말 것.

## 2. 코드가 실제로 Studio에 갔는가 (가장 흔한 착각)

### 2-1. 빠른 대조 — 반드시 CR을 지우고 잰다

Studio의 `Source`는 **CRLF를 LF로 정규화**해서 담는다. 그래서 `wc -c`(원본 바이트)와
`#Source`를 그냥 비교하면 **CRLF 파일마다 줄 수만큼 어긋나 오탐**이 난다. 한 저장소
안에서도 줄바꿈이 섞이므로(에디터·스크립트에 따라 다름) 어떤 파일은 맞고 어떤 파일은
틀리게 나와 더 헷갈린다. **CR을 지우고 재라.**

```bash
tr -d '\r' < src/shared/YourModule.luau | wc -c
```

```lua
-- execute_luau (Edit)
return #game.ReplicatedStorage.Shared.YourModule.Source
```

두 값이 다르면 아직 안 갔다.

⚠️ **길이가 같아도 끊겨 있을 수 있다** — 마지막 편집 이후 그 파일이 안 바뀌었으면 디스크와
Studio가 당연히 같다. 방금 편집한 파일로 재거나, §2-3으로 간다.

### 2-2. 결정적 판정 — 길이 말고 내용

길이는 우연히 같을 수도, 인코딩 때문에 다를 수도 있다. 확실히 하려면 **방금 편집한
고유 문자열**을 찾는다. 추가한 것은 `FOUND`, 삭제한 것은 `absent`여야 한다.

```lua
local src = game.ServerScriptService.Server.YourModule.Source
return string.format("new=%s old=%s",
    tostring(src:find("방금_추가한_함수명", 1, true) ~= nil),
    tostring(src:find("방금_지운_함수명", 1, true) ~= nil))
```

### 2-3. 편집한 파일이 없을 때 — 새 파일 프로브

무엇이 최근에 바뀌었는지 모르면 **디스크에 임시 모듈을 만들어** Studio에 뜨는지 본다.
끊긴 상태에서 확실히 음성이 나오는 유일한 검사다(2026-07-30 실측으로 채택 — 이 검사만이
"ESTABLISHED는 있는데 동기화는 죽음"을 잡아냈다).

```bash
printf 'return {}\n' > src/shared/_SyncProbe.luau
```

```lua
-- execute_luau (Edit)
return game.ReplicatedStorage.Shared:FindFirstChild("_SyncProbe") ~= nil
```

`false`면 끊긴 것. 확인 후 파일을 지우고, **삭제도 반영되는지** 같은 방식으로 본다.

동기화가 확인될 때까지 §1-C를 먼저 해결하고, **그 전에는 어떤 Play 검증도 의미가
없다**(옛 코드를 테스트하게 된다).

## 3. 리그·피직스 헬스체크 (Play)

`start_stop_play(true)` 후 몹/NPC 리그를 덤프한다.

```lua
for _, m in workspace.Mobs:GetChildren() do
    local hum = m:FindFirstChildOfClass("Humanoid")
    if hum then
        -- Count BOTH joint kinds: a rig carrying both has redundant joints (below).
        local motors, constraints, active = 0, 0, 0
        for _, d in m:GetDescendants() do
            if d:IsA("Motor6D") then
                motors += 1
            elseif d:IsA("AnimationConstraint") then
                constraints += 1
                if d.Active then active += 1 end
            end
        end
        print(string.format("%s state=%s hip=%.2f rig=%s motor=%d constraint=%d active=%d",
            m.Name, tostring(hum:GetState()), hum.HipHeight, tostring(hum.RigType),
            motors, constraints, active))
    end
end
```

**알려진 함정 — 증상으로 역추적:**

| 증상 | 원인 | 조치 |
| --- | --- | --- |
| `state=Freefall`인데 바닥 위에 있음 | **HipHeight=0** → 루트가 지면에 파묻혀 다리가 바닥 관통 | HipHeight를 파트 크기로 산출해 설정 |
| HipHeight를 넣었는데 계속 0 | `Humanoid.AutomaticScalingEnabled`가 **부모 연결 시 0으로 되돌림** | 먼저 `false`로 끄고 설정 |
| 애니는 재생되는데 몸이 안 움직임 | 리그에 조인트가 없음 / 관절 타입 불일치(§4) | 조인트 수 확인 |
| 걷기 애니가 안 바뀜 | `Humanoid.Running` 미발화, `MoveDirection`이 0 (§4) | 물리 속도로 판정 |
| `motor>0`이면서 `constraint>0` | **조인트 이중화** — 엔진이 만든 AnimationConstraint 위에 Motor6D를 또 만듦 | 수동 Motor6D 제거(아래) |
| `constraint>0`인데 `active=0` | Motor6D가 제약을 **가리고 있음**(중복의 증상) | 동일 |

**조인트 이중화 — 실제로 물린 사례.** `CreateHumanoidModelFromDescription`으로 만든
리그는 **부모 연결 시 엔진이 AnimationConstraint를 자동 생성**한다(Avatar Joint Upgrade).
그런데 **Edit 모드에서 프로브하면 조인트가 0으로 보이고** `BuildRigFromAttachments()`도
0개를 만든다 — 제약이 런타임에만 생기기 때문이다. 이걸 "엔진이 안 만들어준다"로 오독해
Motor6D를 손으로 만들면, 몹마다 같은 관절에 **조인트가 두 벌** 붙는다(기능은 멀쩡해서
드러나지 않는다).

판별: 위 덤프에서 `motor`와 `constraint`가 **둘 다 0보다 크면** 중복이다. 확인 실험 —
Motor6D를 제거하면 `active`가 0에서 전부 살아나고 애니는 그대로 돈다.

```lua
-- Play에서: 수동 Motor6D를 걷어내고 제약이 깨어나는지 본다
for _, d in mob:GetDescendants() do
    if d:IsA("Motor6D") then d:Destroy() end
end
task.wait(1) -- 이후 active 재측정 + 손 이동으로 애니 확인(§4)
```

`screen_capture`로 배치도 함께 본다(방향 반대·다른 오브젝트에 박힘 등은 수치로 안 잡힌다).

끝나면 `start_stop_play(false)`로 Edit 복귀.

## 4. 계측 함정 — 틀린 도구로 재지 말 것

**음성 결과가 나오면 대상이 아니라 계측기를 먼저 의심한다.** 아래는 전부 실제로
"고장났다"는 오판을 만든 것들이다.

- **`execute_luau`는 러닝 스크립트와 require 캐시를 공유하지 않는다.** Play/Server에서
  실행해도 모듈 **상태**(레지스트리 테이블 등)는 빈 새 인스턴스다 → 상태 의존 API가
  조용히 no-op. **엔진 오브젝트를 직접 조작**하거나 관측 가능한 부수효과로 판정할 것.
- **관절 타입이 리그마다 다르고, 한쪽이 잠들어 있을 수 있다.** 플레이어 R15는
  `AnimationConstraint`(Avatar Joint Upgrade 기본). **`IsA("Motor6D")`는 false**를
  반환하므로 Motor6D를 전제한 코드·계측은 전부 헛돈다. 둘이 공존하면 Motor6D가 이기고
  제약은 `Active=false`로 잠긴다(§3 이중화). 관절 움직임은 **타입 무관 방식**으로 재라 —
  예: 몸통 로컬 좌표계에서 손 위치 변화.
- **래그돌은 제약 유무로 갈린다.** `AnimationConstraint`가 있으면 `IsKinematic=false`
  한 줄이면 되고, 순수 Motor6D 리그는 조인트를 끊고 `BallSocketConstraint`로 갈아야 한다.
  **잠든 제약이 이미 있는데 Motor6D 때문에 "우리는 Motor6D라 어렵다"고 결론 내리기 쉽다** —
  먼저 세어 보라.
- **서버 `MoveTo` 구동 NPC는 `MoveDirection`이 0**이고 `Humanoid.Running`도 안 뜬다.
  25스터드를 걷는 중에도 0.00이었다. → `AssemblyLinearVelocity`의 수평 성분을 쓴다.
- **`AnimationTrack.Length`는 로드 직후 0**이다. `ContentProvider:PreloadAsync` 후 읽거나
  0이 아닐 때까지 폴링한다. 0을 보고 "빈 에셋"이라 단정하지 말 것.
- **짧은 애니는 MCP 호출 사이에 끝난다**(0.4~0.6초). 재생 여부는 나중에 트랙을 훑지 말고
  `Animator.AnimationPlayed`로 **사실을 기록**해 두고 읽는다.
- **텔레그래프형 스킬은 물리 변화가 없다.** "돌진"이 속도 스파이크일 거라 가정했다가
  틀렸다 — 실제로는 Highlight 표시였다. 구현을 먼저 읽고 관측 대상을 정한다.
- **`netstat`의 ESTABLISHED는 "Rojo 연결됨"이 아니다.** Disconnect 후에도 Studio는 소켓을
  물고 있다. 여기서는 오탐이 **양성**으로 난다 — "연결됨"을 보고 안심한 채 옛 코드로
  Play 검증을 돌게 된다. 계층 C는 §2-3으로만 판정한다.
- **`wc -c`와 `#Source`는 CRLF 때문에 어긋난다.** Studio는 LF로 정규화한다(§2-1).
  정상 동기화된 프로젝트를 "미동기화"로 오판하면 **있지도 않은 연결 문제를 쫓게 되므로**
  실제 고장보다 나쁘다. `grep -c $'\r'`로 CRLF를 세는 것도 믿지 말 것 — LF 전용 파일에도
  걸리는 걸 확인했다. 신뢰할 수 있는 건 `tr -d '\r' | wc -c` 비교와 내용 검색뿐이다.

## 5. 보고

**300단어 이내**로. 계층별 상태(A/B/C), 동기화 여부, 리그 이상 목록, 조치한 것과
유저가 직접 해야 할 것을 구분해 적는다. 이상이 없으면 "3층 정상 + 동기화 일치 +
리그 N개 정상" 한 줄로 끝낸다 — 정상일 때 길게 쓰지 않는다.
