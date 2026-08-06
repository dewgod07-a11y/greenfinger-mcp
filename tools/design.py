"""
tools/design.py
카테고리 2: 식물 추천 · 정원 설계 · 관리 가이드 Tools (4개)

  - recommend_plants     : 조건 기반 식물 추천 (T03)
  - design_garden_layout : AI 정원 레이아웃 설계 (T04)
  - get_plant_care_guide : 식물별 관리 가이드 조회 (T05)
  - get_seasonal_tips    : 계절별 원예 작업 안내 (T06)
"""

from __future__ import annotations
import json
import re
from datetime import datetime
from anthropic import AsyncAnthropic
from config.settings import settings
from data.plant_db import PLANT_DB, SEASONAL_TASKS

anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


def _parse_json(raw: str):
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


# ── Tool T03: recommend_plants ───────────────────────────────────────────────
async def recommend_plants(
    space: str = "",
    light: str = "",
    purpose: str = "",
    difficulty: str = "",
) -> dict:
    """
    공간·햇빛·목적 조건에 맞는 식물을 자체 DB에서 추천합니다.

    Args:
        space:      재배 공간 (실내/베란다/옥상/마당, 미입력 시 전체)
        light:      햇빛 조건 (양지/반양지/음지, 미입력 시 전체)
        purpose:    재배 목적 (공기정화/관상/허브/텃밭, 미입력 시 전체)
        difficulty: 관리 난이도 (초보/중급/고급, 미입력 시 전체)
    """
    results = []
    for name, info in PLANT_DB.items():
        if space and not any(space in s for s in info["space"]):
            continue
        if light and light not in info["light"]:
            continue
        if purpose and purpose not in info["purpose"]:
            continue
        if difficulty and difficulty != info["difficulty"]:
            continue
        results.append({
            "name": name,
            "scientific_name": info["scientific_name"],
            "category": info["category"],
            "difficulty": info["difficulty"],
            "light": info["light"],
            "purpose": info["purpose"],
            "description": info["description"],
        })

    return {
        "query": {"space": space, "light": light, "purpose": purpose, "difficulty": difficulty},
        "total_count": len(results),
        "recommendations": results,
        "message": (
            f"조건에 맞는 식물 {len(results)}종을 찾았습니다."
            if results else "조건에 맞는 식물이 없습니다. 조건을 완화해 다시 시도해보세요."
        ),
    }


# ── Tool T04: design_garden_layout ───────────────────────────────────────────
async def design_garden_layout(
    space_type: str,
    space_size: str,
    light_condition: str,
    budget_level: str = "중간",
    preferred_style: str = "",
) -> dict:
    """
    공간 조건을 입력받아 AI가 식물 배치 플랜과 조합을 설계합니다.

    Args:
        space_type:      공간 유형 (베란다/옥상/마당/실내)
        space_size:       공간 크기 (예: 2평, 3m x 1.5m, 소형)
        light_condition:  일조 조건 (양지/반양지/음지)
        budget_level:     예산 수준 (저예산/중간/고예산, 기본: 중간)
        preferred_style:  선호 스타일 (예: 미니멀, 정글룩, 텃밭형)
    """
    style_line = f"선호 스타일: {preferred_style}\n" if preferred_style else ""
    prompt = f"""
당신은 홈가드닝·소규모 조경 설계 전문가입니다.
아래 공간 조건에 맞는 정원 레이아웃을 JSON 형식으로 설계하세요.

공간 유형: {space_type}
공간 크기: {space_size}
일조 조건: {light_condition}
예산 수준: {budget_level}
{style_line}
반드시 아래 JSON 형식으로만 답변하세요 (다른 설명 없이):
{{
  "concept": "정원 컨셉 한 줄 요약",
  "zones": [
    {{
      "zone_name": "구역명 (예: 창가 존)",
      "plants": ["추천 식물1", "식물2"],
      "layout_note": "배치 방법 및 이유",
      "container": "추천 화분/용기 유형"
    }}
  ],
  "estimated_cost_range": "예상 비용 범위 (원)",
  "maintenance_level": "관리 난이도 (낮음/보통/높음)",
  "seasonal_note": "계절 변화 대응 팁"
}}
"""
    try:
        response = await anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json(response.content[0].text)
        if result is not None:
            result["input"] = {
                "space_type": space_type,
                "space_size": space_size,
                "light_condition": light_condition,
                "budget_level": budget_level,
                "preferred_style": preferred_style,
            }
            return result
        return {"error": "AI 응답 파싱 실패"}
    except Exception as e:
        return {"error": f"AI 설계 오류: {str(e)}"}


# ── Tool T05: get_plant_care_guide ───────────────────────────────────────────
async def get_plant_care_guide(
    plant_name: str,
) -> dict:
    """
    식물명으로 물주기·햇빛·비료·분갈이 가이드를 자체 DB에서 조회합니다.

    Args:
        plant_name: 식물명 (예: 몬스테라, 로즈마리, 방울토마토)
    """
    info = PLANT_DB.get(plant_name)
    if info is None:
        matches = [n for n in PLANT_DB if plant_name in n or n in plant_name]
        if matches:
            info = PLANT_DB[matches[0]]
            plant_name = matches[0]
        else:
            return {
                "plant_name": plant_name,
                "found": False,
                "message": f"'{plant_name}'은(는) 현재 자체 DB에 등록되어 있지 않습니다.",
                "available_plants": sorted(PLANT_DB.keys()),
            }

    return {
        "plant_name": plant_name,
        "found": True,
        "scientific_name": info["scientific_name"],
        "category": info["category"],
        "difficulty": info["difficulty"],
        "light": info["light"],
        "water_frequency": info["water_frequency"],
        "temperature": info["temperature"],
        "care_guide": info["care_guide"],
        "seasonal_care": info["seasonal_care"],
        "major_pests": info["major_pests"],
    }


# ── Tool T06: get_seasonal_tips ──────────────────────────────────────────────
async def get_seasonal_tips(
    month: int = 0,
) -> dict:
    """
    현재 월 기준 계절별 원예 작업 목록과 관리 팁을 자체 DB에서 조회합니다.

    Args:
        month: 조회 월 (1~12, 0이면 현재 월 자동 적용)
    """
    if month == 0:
        month = datetime.now().month

    info = SEASONAL_TASKS.get(month)
    if info is None:
        return {"error": "month는 1~12 사이여야 합니다.", "month": month}

    return {
        "month": month,
        "season": info["season"],
        "tasks": info["tasks"],
        "tip": info["tip"],
    }
