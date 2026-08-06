"""
tools/pots.py
카테고리: 화분 관리 Tools (3개)
  - recommend_pot_size    : 식물에 맞는 화분 사이즈·재질·분갈이 시기 추천
  - diagnose_pot_condition : 화분 증상(뿌리 노출·배수 불량 등) 기반 분갈이 시급도 AI 진단
  - manage_my_pots         : 내가 키우는 화분 등록/목록조회/삭제 (인메모리)
"""
from __future__ import annotations
import json
import re
import uuid
from datetime import datetime
from anthropic import AsyncAnthropic
from config.settings import settings
from data.plant_db import PLANT_DB

anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

# ── 간단한 인메모리 화분 인벤토리 (실제 배포 시 DB로 교체) ────────────────────
_MY_POTS: list[dict] = []


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


async def recommend_pot_size(
    plant_name: str,
    current_pot_diameter_cm: int = 0,
) -> dict:
    """
    식물명(과 현재 화분 크기)을 입력받아 적정 화분 재질·사이즈·분갈이 필요 여부를 추천합니다.

    Args:
        plant_name:               식물명 (예: 몬스테라, 방울토마토)
        current_pot_diameter_cm:  현재 사용 중인 화분 지름(cm), 0이면 비교 없이 일반 가이드만 제공
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

    pot_guide = info["pot_guide"]
    seedling_d = pot_guide["seedling_diameter_cm"]
    mature_d = pot_guide["mature_diameter_cm"]

    needs_repot = None
    recommended_next_diameter_cm = None
    advice = f"모종 시기 {seedling_d}cm → 성숙기 최대 {mature_d}cm 화분을 기준으로 단계적으로 키워주세요."

    if current_pot_diameter_cm and current_pot_diameter_cm > 0:
        if current_pot_diameter_cm >= mature_d:
            needs_repot = False
            advice = "현재 화분이 이미 충분히 크므로 당장 분갈이는 필요하지 않습니다."
        else:
            needs_repot = True
            recommended_next_diameter_cm = min(current_pot_diameter_cm + 5, mature_d)
            advice = (
                f"현재 {current_pot_diameter_cm}cm 화분보다 한 치수 큰 "
                f"{recommended_next_diameter_cm}cm 화분으로 분갈이를 권장합니다."
            )

    return {
        "plant_name": plant_name,
        "found": True,
        "seedling_pot_diameter_cm": seedling_d,
        "mature_pot_diameter_cm": mature_d,
        "preferred_material": pot_guide["preferred_material"],
        "drainage_requirement": pot_guide["drainage_requirement"],
        "current_pot_diameter_cm": current_pot_diameter_cm or None,
        "needs_repot": needs_repot,
        "recommended_next_diameter_cm": recommended_next_diameter_cm,
        "advice": advice,
    }


async def diagnose_pot_condition(
    plant_name: str,
    symptoms: str,
    current_pot_diameter_cm: int = 0,
) -> dict:
    """
    화분 관련 증상(배수구로 뿌리 노출, 물이 안 빠짐, 화분이 가벼워짐 등)을 입력받아
    분갈이 시급도와 원인을 AI로 진단합니다. 일반적인 화분 사이즈 가이드만 필요하면
    recommend_pot_size를 사용하세요.

    Args:
        plant_name:               식물명 (예: 몬스테라, 산세베리아)
        symptoms:                 관찰된 화분 증상 (예: 배수구멍으로 뿌리가 삐져나옴, 물을 줘도 겉으로 바로 흘러내림)
        current_pot_diameter_cm:  현재 화분 지름(cm), 0이면 미입력
    """
    info = PLANT_DB.get(plant_name)
    if info is None:
        matches = [n for n in PLANT_DB if plant_name in n or n in plant_name]
        if matches:
            info = PLANT_DB[matches[0]]
            plant_name = matches[0]

    db_context = ""
    if info:
        pg = info["pot_guide"]
        db_context = (
            f"참고 DB 정보 — 성숙기 권장 화분 지름: {pg['mature_diameter_cm']}cm, "
            f"선호 재질: {', '.join(pg['preferred_material'])}, 배수 요구도: {pg['drainage_requirement']}\n"
        )
    pot_line = f"현재 화분 지름: {current_pot_diameter_cm}cm\n" if current_pot_diameter_cm else ""

    prompt = f"""
당신은 홈가드닝 화분·분갈이 전문가입니다.
아래 화분 증상을 분석해 분갈이 시급도와 원인을 JSON 형식으로 진단하세요.

식물명: {plant_name}
증상: {symptoms}
{pot_line}{db_context}
반드시 아래 JSON 형식으로만 답변하세요 (다른 설명 없이):
{{
  "urgency": "높음/보통/낮음",
  "root_bound_likely": true,
  "cause_analysis": "증상이 나타나는 원인 설명 (2~3문장)",
  "recommended_action": "지금 취해야 할 조치",
  "recommended_pot_diameter_cm": 0,
  "timing_advice": "분갈이 적기 안내 (예: 지금 바로/이번 계절 내/다음 생장기까지 대기 가능)"
}}
"""
    try:
        response = await anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json(response.content[0].text)
        if result is None:
            result = {"error": "AI 응답 파싱 실패"}
    except Exception as e:
        result = {"error": f"AI 진단 오류: {str(e)}"}

    result["input"] = {
        "plant_name": plant_name,
        "symptoms": symptoms,
        "current_pot_diameter_cm": current_pot_diameter_cm or None,
    }
    return result


async def manage_my_pots(
    action: str,
    pot_name: str = "",
    plant_name: str = "",
    location: str = "",
    pot_diameter_cm: int = 0,
    pot_id: str = "",
) -> dict:
    """
    내가 키우는 화분을 등록·조회·삭제합니다.

    Args:
        action:          수행할 작업 (register: 등록 / list: 목록조회 / remove: 삭제)
        pot_name:        화분 별칭 (예: 거실_몬스테라, register 시 필수)
        plant_name:      식물명 (register 시 필수, list 시 필터로 사용 가능)
        location:        배치 위치 (예: 거실 창가, 베란다, list 시 필터로 사용 가능)
        pot_diameter_cm: 화분 지름(cm)
        pot_id:          화분 ID (remove 시 필수)
    """
    if action == "register":
        if not pot_name or not plant_name:
            return {"error": "register 액션에는 pot_name과 plant_name이 필요합니다."}
        record = {
            "pot_id": str(uuid.uuid4())[:8].upper(),
            "pot_name": pot_name,
            "plant_name": plant_name,
            "location": location,
            "pot_diameter_cm": pot_diameter_cm or None,
            "registered_at": datetime.now().isoformat(),
        }
        _MY_POTS.append(record)
        return {"success": True, "pot": record, "message": f"✅ '{pot_name}' 화분이 등록되었습니다."}

    if action == "list":
        results = list(_MY_POTS)
        if plant_name:
            results = [p for p in results if plant_name.lower() in p["plant_name"].lower()]
        if location:
            results = [p for p in results if location in p["location"]]
        return {"total_count": len(results), "pots": results}

    if action == "remove":
        if not pot_id:
            return {"error": "remove 액션에는 pot_id가 필요합니다."}
        before = len(_MY_POTS)
        _MY_POTS[:] = [p for p in _MY_POTS if p["pot_id"] != pot_id]
        removed = before - len(_MY_POTS)
        return {
            "success": removed > 0,
            "message": "✅ 삭제되었습니다." if removed > 0 else f"pot_id '{pot_id}'를 찾을 수 없습니다.",
        }

    return {"error": "action은 register/list/remove 중 하나여야 합니다."}
