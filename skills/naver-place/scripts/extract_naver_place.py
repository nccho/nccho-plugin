#!/usr/bin/env python3
"""네이버 플레이스 정보 추출기.

사용법:
    python3 extract_naver_place.py <place_id | m.place URL | map.naver 링크>

동작:
  1) 입력에서 place_id 를 뽑는다 (naver.me 단축링크는 먼저 리다이렉트를 따라간다).
  2) m.place.naver.com 의 home / review 페이지를 브라우저 헤더 curl 로 받는다.
     (WebFetch 가 차단되는 사이트라 curl 폴백을 쓴다 — fetch-blocked 스킬 참고)
  3) 페이지에 박힌 window.__APOLLO_STATE__ (GraphQL 캐시 JSON) 를 파싱해
     필요한 필드만 골라 깨끗한 JSON 으로 stdout 에 출력한다.

출력은 JSON 하나. 원본 HTML(수백 KB)은 절대 stdout 으로 내보내지 않는다.
"""
import json
import re
import subprocess
import sys
import urllib.request

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")


def resolve_place_id(arg: str) -> str:
    """URL/ID 어느 형태로 줘도 숫자 place_id 를 돌려준다."""
    if arg.isdigit():
        return arg
    m = re.search(r"/place/(\d+)", arg)
    if m:
        return m.group(1)
    # naver.me 단축링크 → 리다이렉트 Location 헤더에서 뽑는다
    if "naver.me" in arg:
        req = urllib.request.Request(arg, method="GET", headers={"User-Agent": UA})
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:  # 307 등은 여기로 안 옴, 아래 fallback
            loc = e.headers.get("Location", "")
            m = re.search(r"/place/(\d+)", loc) or re.search(r"place/(\d+)", loc)
            if m:
                return m.group(1)
        except Exception:
            pass
    # curl 로 리다이렉트 헤더만 확인 (가장 확실)
    out = subprocess.run(
        ["curl", "-sIL", "-A", UA, arg],
        capture_output=True, text=True, timeout=20,
    ).stdout
    m = re.search(r"/place/(\d+)", out)
    if m:
        return m.group(1)
    raise SystemExit(f"place_id 를 찾지 못했습니다: {arg}")


def fetch(url: str) -> str:
    out = subprocess.run(
        ["curl", "-sL", "-A", UA, "-H", "Accept-Language: ko-KR,ko;q=0.9", url],
        capture_output=True, text=True, timeout=30,
    )
    return out.stdout


def apollo_state(html: str) -> dict:
    """window.__APOLLO_STATE__ = {...} 의 JSON 객체를 중괄호 균형으로 잘라 파싱."""
    i = html.find("window.__APOLLO_STATE__")
    if i < 0:
        return {}
    i = html.find("{", i)
    depth, in_str, esc = 0, False, False
    for j in range(i, len(html)):
        c = html[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(html[i:j + 1])
                    except json.JSONDecodeError:
                        return {}
    return {}


def pick(state: dict) -> dict:
    """Apollo flat cache 에서 관심 필드만 골라낸다. type 이름 변경에 강하도록
    __typename 이 아니라 '들어있는 키'로 찾는다."""
    vals = [v for v in state.values() if isinstance(v, dict)]
    base, menus, themes, booking = {}, [], [], {}

    for v in vals:
        if "roadAddress" in v and "name" in v and not base:
            coord = v.get("coordinate") or {}
            base = {
                "name": v.get("name"),
                "category": v.get("category"),
                "roadAddress": v.get("roadAddress"),
                "address": v.get("address"),
                "phone": v.get("virtualPhone") or v.get("phone"),
                "lat": coord.get("y"),
                "lng": coord.get("x"),
            }
        # 메뉴: name + price 를 동시에 가진 항목
        if "price" in v and "name" in v and v.get("price") not in (None, "가격"):
            menus.append({"name": v.get("name"),
                          "price": v.get("price"),
                          "desc": v.get("description")})
        # 예약/주문 단서
        for k in ("bookingUrl", "bookingBusinessId", "naverBookingUrl"):
            if v.get(k):
                booking[k] = v.get(k)

    # 테마 키워드 (별점 대체 지표)
    def walk(o):
        if isinstance(o, dict):
            if o.get("__typename", "").startswith("VisitorReviewStatsAnalysisThemes"):
                themes.append({"label": o.get("label"), "count": o.get("count")})
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(state)

    # 영업시간: WorkingHoursInfo 노드가 중첩 인라인으로 박혀 있어 재귀로 훑는다.
    hours, status = [], None

    def walk_hours(o):
        nonlocal status
        if isinstance(o, dict):
            if o.get("__typename") == "WorkingHoursInfo":
                bh = o.get("businessHours") or {}
                breaks = [{"start": b.get("start"), "end": b.get("end")}
                          for b in (o.get("breakHours") or [])
                          if isinstance(b, dict) and b.get("start")]
                hours.append({"day": o.get("day"),
                              "start": bh.get("start"), "end": bh.get("end"),
                              "breaks": breaks})
            if o.get("__typename") == "BusinessStatusDescription" and not status:
                status = o.get("description") or o.get("status")
            for x in o.values():
                walk_hours(x)
        elif isinstance(o, list):
            for x in o:
                walk_hours(x)
    walk_hours(state)

    # 중복 제거(같은 day/start/end)
    seen, uniq = set(), []
    for h in hours:
        key = (h["day"], h["start"], h["end"])
        if key not in seen:
            seen.add(key)
            uniq.append(h)

    return {"base": base, "menus": menus, "hours": uniq, "status": status,
            "themes": themes, "booking": booking}


def reviews(state: dict, limit: int = 8) -> list:
    out = []
    for v in state.values():
        if isinstance(v, dict) and v.get("__typename") == "VisitorReview":
            body = v.get("body")
            if body:
                out.append({"body": body, "created": v.get("created")})
    return out[:limit]


def break_hints(*htmls) -> list:
    """구조화된 breakHours 가 비어도, 식당은 브레이크 타임이 리뷰/설명 텍스트에만
    적혀 있는 경우가 많다. '브레이크' 근처의 HH:MM-HH:MM 시간대를 폴백으로 긁는다."""
    text = " ".join(htmls)
    text = re.sub(r"\s+", " ", text)
    rng = r"(\d{1,2}\s*:\s*\d{2})\s*[-~]\s*(\d{1,2}\s*:\s*\d{2})"
    hints = []
    for m in re.finditer(r"브레이크\s*타?임?[^0-9]{0,8}" + rng, text):
        norm = lambda s: re.sub(r"\s+", "", s)
        hints.append(f"{norm(m.group(1))}-{norm(m.group(2))}")
    # 중복 제거, 최대 3개
    seen, out = set(), []
    for h in hints:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out[:3]


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: extract_naver_place.py <place_id | url>")
    pid = resolve_place_id(sys.argv[1])
    home_html = fetch(f"https://m.place.naver.com/place/{pid}/home")
    rev_html = fetch(f"https://m.place.naver.com/place/{pid}/review/visitor")
    home = apollo_state(home_html)
    rev = apollo_state(rev_html)
    result = pick(home)
    result["place_id"] = pid
    result["url"] = f"https://map.naver.com/p/entry/place/{pid}"
    result["review_count_theme"] = result.pop("themes")
    # 예약 단서가 home 에 없으면 review 캐시에서도 한 번 더 본다
    if not result["booking"]:
        result["booking"] = pick(rev).get("booking", {})
    result["reviews"] = reviews(rev)
    # 구조화된 브레이크가 하나도 없으면 텍스트에서 폴백 추출 (리뷰 언급 기준)
    has_struct_break = any(h.get("breaks") for h in result.get("hours", []))
    result["break_time_from_text"] = [] if has_struct_break else break_hints(home_html, rev_html)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
