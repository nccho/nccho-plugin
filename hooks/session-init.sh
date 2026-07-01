#!/bin/bash
# ~/.claude/hooks/session-init.sh
# 세션 시작 시 에이전트 모델 선택 규칙을 context에 주입

cat << 'ENDJSON'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "## 에이전트 선택 규칙 (필수 준수)\n\nAgent() 호출 시 반드시 아래 기준으로 에이전트를 선택하세요:\n\n**searcher (Haiku)**\n- 파일 검색, 내용 읽기, git log/status, grep, 디렉토리 탐색\n- 코드 수정 없이 정보만 필요할 때\n\n**implementer (Sonnet)**\n- 코드 작성, 기능 구현, 버그 수정, 리팩터링, 테스트 작성\n- 파일을 생성하거나 수정해야 할 때\n\n**analyzer (Opus)**\n- 아키텍처 설계, 심층 코드 리뷰, 보안 분석, 기술 비교\n- 복잡한 추론이나 전략적 판단이 필요할 때\n\n판단이 어려우면 implementer(Sonnet)를 기본으로 사용하세요."
  }
}
ENDJSON
