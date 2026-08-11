"""
utils/rate_limit.py
Claude API(AI) 호출 전역 사용량 제한

PlayMCP에 공개 등록되면 불특정 다수가 diagnose_plant_disease 등 AI 기반
Tool을 호출할 수 있고, 그때마다 서버 소유자의 ANTHROPIC_API_KEY로 과금됩니다.
트래픽이 튀어도 예상치 못한 비용이 나가지 않도록 시간당 호출 횟수를 제한합니다.
(단일 프로세스 인메모리 카운터 — 다중 인스턴스 배포 시에는 별도 저장소가 필요합니다.)
"""
from __future__ import annotations
import os
import time
from collections import deque

_MAX_CALLS_PER_HOUR = int(os.getenv("AI_CALL_LIMIT_PER_HOUR", "50"))
_WINDOW_SECONDS = 3600
_call_times: deque[float] = deque()


def check_ai_rate_limit() -> str | None:
    """
    AI 호출이 가능하면 None을 반환합니다.
    시간당 한도를 초과했으면 사용자에게 보여줄 안내 메시지를 반환합니다
    (이 경우 호출부는 Claude API를 부르지 않고 바로 이 메시지를 반환해야 합니다).
    """
    now = time.monotonic()
    while _call_times and now - _call_times[0] > _WINDOW_SECONDS:
        _call_times.popleft()

    if len(_call_times) >= _MAX_CALLS_PER_HOUR:
        return (
            f"현재 AI 진단·설계 요청이 많아 시간당 한도({_MAX_CALLS_PER_HOUR}회)에 도달했습니다. "
            "잠시 후 다시 시도해주세요."
        )

    _call_times.append(now)
    return None
