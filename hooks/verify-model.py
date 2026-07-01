#!/usr/bin/env python3
# hooks/verify-model.py
# SubagentStart 훅: 에이전트-모델 매핑 검증 및 로그 기록 (플러그인 버전)

import json, sys, os, re
from datetime import datetime

EXPECTED_MODELS = {
    "searcher":    "haiku",
    "implementer": "sonnet",
    "analyzer":    "opus",
}

LOG_FILE = os.path.expanduser('~/.claude/model-routing.log')
# 플러그인 내부 agents 디렉토리 (설치 위치에 무관하게 동작)
PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
PLUGIN_AGENTS_DIR = os.path.join(PLUGIN_ROOT, 'agents') if PLUGIN_ROOT else ''


def get_model_from_agent_file(agent_type, cwd):
    """프로젝트 .claude/agents/ 우선, 없으면 플러그인 agents/ 에서 model: 필드 읽기"""
    candidates = [
        os.path.join(cwd, '.claude', 'agents', f'{agent_type}.md'),
    ]
    if PLUGIN_AGENTS_DIR:
        candidates.append(os.path.join(PLUGIN_AGENTS_DIR, f'{agent_type}.md'))
    for path in candidates:
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            match = re.search(r'^model:\s*(\S+)', content, re.MULTILINE)
            return match.group(1) if match else None
    return None


def log(message):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a') as f:
        f.write(f'[{ts}] {message}\n')


data = json.load(sys.stdin)
agent_type = data.get('agent_type', 'unknown')
agent_id   = data.get('agent_id', 'unknown')
cwd        = data.get('cwd', '.')

actual_model   = get_model_from_agent_file(agent_type, cwd)
expected_model = EXPECTED_MODELS.get(agent_type)

if agent_type not in EXPECTED_MODELS:
    log(f'[INFO]  Built-in agent started: {agent_type} (id={agent_id})')
elif actual_model and actual_model != expected_model:
    msg = (f'[WARN]  Model mismatch! agent={agent_type} '
           f'expected={expected_model} actual={actual_model}')
    log(msg)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": f"⚠️ 모델 불일치 경고: {agent_type} 에이전트의 모델이 {actual_model}로 설정되어 있으나 {expected_model}이 기대됩니다."
        }
    }
    print(json.dumps(output, ensure_ascii=False))
else:
    log(f'[OK]    {agent_type} started with {actual_model} (id={agent_id})')
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": f"✅ {agent_type} 에이전트가 {actual_model} 모델로 정상 실행 중"
        }
    }
    print(json.dumps(output, ensure_ascii=False))

sys.exit(0)
