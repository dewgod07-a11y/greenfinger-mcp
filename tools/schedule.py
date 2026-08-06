"""
tools/schedule.py
카테고리 4: 관리 일정·알림 Tools (2개)
  - create_garden_schedule  : 일정 등록 + 카카오 캘린더 연동 (T07)
  - send_garden_reminder    : 카카오톡 나와의 채팅 알림 발송 (T08)

카카오 캘린더/톡 일정 등록·발송은 PlayMCP 도구함에 함께 활성화된
'카카오 톡캘린더 MCP'(KakaotalkCal-CreateEvent), '카카오톡 나와의채팅 MCP'
(KakaotalkChat-MemoChat)를 AI가 이어서 호출하는 방식으로 동작합니다.
그린핑거 MCP는 사용자 OAuth 토큰을 직접 보관하지 않으므로, 두 도구의
파라미터 스키마에 맞춘 제안 값(calendar_event_suggestion / chat_message_suggestion)을
반환해 AI가 바로 이어 호출할 수 있게 합니다.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timedelta
from data.plant_db import PLANT_DB, SEASONAL_TASKS

# ── 간단한 인메모리 이력 저장 (실제 배포 시 DB로 교체) ────────────────────────
_CARE_DB: list[dict] = []

_CARE_TYPE_EMOJI = {
    "물주기": "💧",
    "비료": "🌱",
    "가지치기": "✂️",
    "분갈이": "🪴",
    "파종": "🌾",
    "수확": "🧺",
    "병충해방제": "🐛",
}

_COLOR_BY_CARE_TYPE = {
    "물주기": "BLUE",
    "비료": "ORANGE",
    "가지치기": "GREEN",
    "분갈이": "BROWN",
    "파종": "LIME",
    "수확": "MINT",
    "병충해방제": "RED",
}


def _add_minutes(hhmm: str, minutes: int) -> str:
    t = datetime.strptime(hhmm, "%H:%M") + timedelta(minutes=minutes)
    return t.strftime("%H:%M")


def _build_rrule(repeat_every_days: int, repeat_count: int) -> str:
    rrule = "FREQ=DAILY" if repeat_every_days == 1 else f"FREQ=DAILY;INTERVAL={repeat_every_days}"
    if repeat_count and repeat_count > 0:
        rrule += f";COUNT={repeat_count}"
    return rrule


def _find_plant(plant_name: str) -> dict | None:
    info = PLANT_DB.get(plant_name)
    if info is not None:
        return info
    matches = [n for n in PLANT_DB if plant_name in n or n in plant_name]
    return PLANT_DB[matches[0]] if matches else None


def _season_for_date(scheduled_date: str) -> str:
    month = int(scheduled_date.split("-")[1])
    return SEASONAL_TASKS.get(month, {}).get("season", "")


async def create_garden_schedule(
    plant_name: str,
    care_type: str,
    scheduled_date: str,
    scheduled_time: str = "09:00",
    notes: str = "",
    reminder_minutes: int = 0,
    repeat_every_days: int = 0,
    repeat_count: int = 0,
) -> dict:
    """
    식물 관리 일정(물주기·비료·가지치기 등)을 등록하고, 카카오 캘린더에
    바로 등록할 수 있는 이벤트 제안 값을 함께 반환합니다.

    care_type이 '물주기'이고 repeat_every_days를 지정하지 않으면, 자체 DB의
    계절별 물주기 간격(plant_db.watering_interval_days)을 기준으로 반복 주기를
    자동 계산합니다 (식물별 정보가 없으면 반복 없이 1회성 일정으로 등록).
    물주기 알림 문구에는 항상 "고정 알림은 참고용이며 흙 상태를 먼저 확인하라"는
    안내가 포함됩니다 — 실제 물주기는 계절·화분 재질·날씨에 따라 달라지기 때문입니다.

    Args:
        plant_name:        대상 식물명 또는 위치명 (예: 베란다_몬스테라_1번)
        care_type:         관리 유형 (물주기/비료/가지치기/분갈이/파종/수확/병충해방제)
        scheduled_date:    최초 예정 날짜 (YYYY-MM-DD)
        scheduled_time:    예정 시각 (HH:MM, 5분 단위, 기본: 09:00)
        notes:             특이사항 메모
        reminder_minutes:  시작 전 알림 시간(분 단위), 0이면 알림 없음
        repeat_every_days: N일마다 반복 (0이면 물주기는 계절별 자동 계산, 그 외는 반복 없음)
        repeat_count:       반복 횟수 (0이면 종료일 없이 계속 반복)
    """
    try:
        datetime.strptime(scheduled_date, "%Y-%m-%d")
        datetime.strptime(scheduled_time, "%H:%M")
    except ValueError:
        return {"error": "날짜는 YYYY-MM-DD, 시각은 HH:MM 형식으로 입력하세요."}

    if int(scheduled_time.split(":")[1]) % 5 != 0:
        return {"error": "scheduled_time의 분(minute)은 5분 단위여야 합니다."}

    if repeat_every_days < 0 or repeat_count < 0:
        return {"error": "repeat_every_days와 repeat_count는 0 이상이어야 합니다."}

    auto_interval_used = False
    season = ""
    if care_type == "물주기" and repeat_every_days == 0:
        plant_info = _find_plant(plant_name)
        season = _season_for_date(scheduled_date)
        if plant_info and season:
            interval = plant_info.get("watering_interval_days", {}).get(season)
            if interval:
                repeat_every_days = interval
                auto_interval_used = True

    record_id = str(uuid.uuid4())[:8].upper()
    record = {
        "record_id": record_id,
        "plant_name": plant_name,
        "care_type": care_type,
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
        "notes": notes,
        "repeat_every_days": repeat_every_days or None,
        "repeat_count": repeat_count or None,
        "status": "예정",
        "created_at": datetime.now().isoformat(),
    }
    _CARE_DB.append(record)

    emoji = _CARE_TYPE_EMOJI.get(care_type, "🌿")
    end_time = _add_minutes(scheduled_time, 30)
    title = f"{emoji} [{care_type}] {plant_name}"[:50]

    description = notes or f"그린핑거 MCP로 등록된 {plant_name} {care_type} 일정입니다."
    if care_type == "물주기":
        description += "\n💡 고정 알림은 참고용입니다 — 흙 표면을 먼저 확인하고 마른 경우에만 물을 주세요."
        if auto_interval_used:
            description += f" ({season} 기준 자동 추천 간격: {repeat_every_days}일)"

    calendar_event_suggestion = {
        "title": title,
        "time": {
            "startAt": f"{scheduled_date}T{scheduled_time}:00",
            "endAt": f"{scheduled_date}T{end_time}:00",
        },
        "description": description,
        "color": _COLOR_BY_CARE_TYPE.get(care_type, "GREEN"),
    }
    if reminder_minutes and reminder_minutes > 0:
        calendar_event_suggestion["reminders"] = [reminder_minutes]
    if repeat_every_days and repeat_every_days > 0:
        calendar_event_suggestion["recurrence"] = _build_rrule(repeat_every_days, repeat_count)

    if repeat_every_days:
        repeat_desc = f"{repeat_every_days}일마다" + (f" {repeat_count}회" if repeat_count else " 계속") + " 반복"
        if auto_interval_used:
            repeat_desc += f" ({season} 계절 자동 추천)"
    else:
        repeat_desc = "반복 없음"

    return {
        "success": True,
        "record_id": record_id,
        "plant_name": plant_name,
        "care_type": care_type,
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
        "notes": notes,
        "repeat": repeat_desc,
        "auto_interval_used": auto_interval_used,
        "calendar_event_suggestion": calendar_event_suggestion,
        "next_step": (
            "이 calendar_event_suggestion 값을 그대로 카카오 톡캘린더 등록 도구"
            "(KakaotalkCal-CreateEvent)에 전달해 등록을 완료하세요. 등록 전 사용자에게 "
            "제목·일시·반복 주기를 확인받아야 합니다."
        ),
        "message": f"✅ {plant_name} {care_type} 일정이 {scheduled_date} {scheduled_time}로 준비되었습니다 ({repeat_desc}).",
    }


async def send_garden_reminder(
    message: str,
    plant_info: str = "",
    next_care_date: str = "",
    urgency: str = "일반",
) -> dict:
    """
    식물 관리 알림 메시지를 만들고, 카카오톡 나와의 채팅으로 바로 보낼 수 있는
    발송 제안 값을 반환합니다.

    Args:
        message:        알림 내용
        plant_info:     대상 식물 정보 (식물명, 위치)
        next_care_date: 다음 관리 예정일 (YYYY-MM-DD)
        urgency:        긴급도 (일반/주의/긴급, 기본: 일반)
    """
    urgency_emoji = {"일반": "🌿", "주의": "⚠️", "긴급": "🚨"}.get(urgency, "🌿")

    full_message = f"{urgency_emoji} [식물 관리 알림]\n\n{message}"
    if plant_info:
        full_message += f"\n\n📍 대상: {plant_info}"
    if next_care_date:
        full_message += f"\n📅 다음 관리 예정: {next_care_date}"
    full_message += "\n\n- 그린핑거 MCP -"

    # KakaotalkChat-MemoChat 의 message는 최대 200자
    if len(full_message) > 200:
        chat_message_suggestion = full_message[:197] + "..."
    else:
        chat_message_suggestion = full_message

    return {
        "urgency": urgency,
        "full_message": full_message,
        "chat_message_suggestion": chat_message_suggestion,
        "next_step": (
            "chat_message_suggestion 값을 그대로 카카오톡 나와의 채팅 발송 도구"
            "(KakaotalkChat-MemoChat)의 message 인자에 전달해 발송을 완료하세요."
        ),
    }
