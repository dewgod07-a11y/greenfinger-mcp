"""
tools/diagnosis.py
카테고리 1: 식물 병해충 진단·식별 Tools (3개)

  - diagnose_plant_disease  : 증상 텍스트 → 병해충 진단 (T01)
  - diagnose_plant_by_image : 사진 URL  → AI 비전 진단 (T02)
  - identify_plant_by_image : 사진 URL  → 병해충 진단 없이 식물 종만 식별
"""

from __future__ import annotations
import json
import re
from anthropic import AsyncAnthropic
from config.settings import settings
from data.plant_db import PLANT_DB
from utils.rate_limit import check_ai_rate_limit

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


# ── Tool T01: diagnose_plant_disease ─────────────────────────────────────────
async def diagnose_plant_disease(
    plant_name: str,
    symptoms: str,
    location: str = "전체",
    care_environment: str = "",
) -> dict:
    """
    식물의 증상을 텍스트로 입력받아 병해충을 진단하고 초기 대응 방법을 반환합니다.

    Args:
        plant_name:       식물명 (예: 몬스테라, 바질, 방울토마토)
        symptoms:         증상 설명 (예: 잎이 노랗게 변하고 끝이 마름)
        location:         발생 부위 (잎/줄기/뿌리/전체)
        care_environment: 재배 환경 (예: 베란다 서향, 실내 반양지)
    """
    limit_message = check_ai_rate_limit()
    if limit_message:
        return {"error": limit_message}

    env_line = f"재배 환경: {care_environment}\n" if care_environment else ""
    prompt = f"""
당신은 홈가드닝·생활 원예 전문가입니다.
아래 식물 증상을 분석하여 JSON 형식으로 진단 결과를 반환하세요.

식물명: {plant_name}
증상: {symptoms}
발생 부위: {location}
{env_line}
반드시 아래 JSON 형식으로만 답변하세요 (다른 설명 없이):
{{
  "diagnoses": [
    {{
      "issue_name": "병해충 또는 생리장해명",
      "probability": "높음/보통/낮음",
      "description": "설명 (2~3문장)",
      "symptoms_match": "증상 일치 이유",
      "immediate_action": "즉시 취해야 할 조치",
      "treatment": "처치 방법",
      "severity": "경미/보통/심각"
    }}
  ],
  "general_advice": "전반적인 관리 조언",
  "need_expert": false
}}
"""
    try:
        response = await anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json(response.content[0].text)
        if result is None:
            result = {"diagnoses": [], "general_advice": "AI 응답 파싱 실패", "need_expert": True}
    except Exception as e:
        result = {"diagnoses": [], "general_advice": f"AI 진단 오류: {str(e)}", "need_expert": True}

    result["input"] = {
        "plant_name": plant_name,
        "symptoms": symptoms,
        "location": location,
        "care_environment": care_environment,
    }
    return result


# ── Tool T02: diagnose_plant_by_image ────────────────────────────────────────
async def diagnose_plant_by_image(
    image_url: str,
    plant_name: str = "모름",
    location: str = "",
) -> dict:
    """
    사용자가 실제 사진 URL을 직접 제공한 경우에만 사용합니다.
    증상을 텍스트로 설명하는 경우는 diagnose_plant_disease를 사용하세요.
    image_url은 절대 임의로 생성하거나 예시 URL을 사용하지 마세요.

    Args:
        image_url:  사용자가 제공한 식물 사진 URL (반드시 실제 URL이어야 함)
        plant_name: 식물명 (모를 경우 '모름' 입력)
        location:   촬영 위치 (예: 베란다, 옥상 텃밭)
    """
    limit_message = check_ai_rate_limit()
    if limit_message:
        return {"error": limit_message, "image_url": image_url}

    prompt = f"""
당신은 홈가드닝·생활 원예 전문가입니다.
첨부된 식물 사진을 보고 병해충 또는 생리장해 여부를 진단하세요.

알려진 식물명: {plant_name}
촬영 위치: {location if location else '미입력'}

반드시 아래 JSON 형식으로만 답변하세요:
{{
  "detected_plant": "사진에서 식별된 식물명",
  "visible_symptoms": ["관찰된 증상1", "관찰된 증상2"],
  "diagnoses": [
    {{
      "issue_name": "병해충 또는 생리장해명",
      "confidence": "높음/보통/낮음",
      "description": "설명",
      "treatment": "처치 방법"
    }}
  ],
  "image_quality": "진단에 충분함/불충분함",
  "recommendation": "추가 조치 권고 및 이유"
}}
"""
    try:
        response = await anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "url", "url": image_url}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        result = _parse_json(response.content[0].text)
        if result is not None:
            return result
        return {"error": "AI 응답 파싱 실패", "image_url": image_url}
    except Exception as e:
        return {"error": f"AI 비전 진단 오류: {str(e)}", "image_url": image_url}


# ── identify_plant_by_image ───────────────────────────────────────────────────
async def identify_plant_by_image(
    image_url: str,
) -> dict:
    """
    사진 URL로 병해충 진단 없이 식물 종만 식별합니다. "이 식물 이름이 뭐야?" 처럼
    순수 식별만 필요할 때 사용하세요. 증상이 있어 진단이 필요하면
    diagnose_plant_by_image를 사용하세요.
    image_url은 절대 임의로 생성하거나 예시 URL을 사용하지 마세요.

    Args:
        image_url: 사용자가 제공한 식물 사진 URL (반드시 실제 URL이어야 함)
    """
    limit_message = check_ai_rate_limit()
    if limit_message:
        return {"error": limit_message, "image_url": image_url}

    prompt = """
당신은 식물 분류 전문가입니다. 첨부된 사진 속 식물 종을 식별하세요.

반드시 아래 JSON 형식으로만 답변하세요:
{
  "identified_name": "한국 통용명 (예: 몬스테라)",
  "scientific_name": "학명",
  "confidence": "높음/보통/낮음",
  "characteristics": "식별 근거가 된 외형 특징 (1~2문장)",
  "image_quality": "식별에 충분함/불충분함"
}
"""
    try:
        response = await anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "url", "url": image_url}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        result = _parse_json(response.content[0].text)
        if result is None:
            return {"error": "AI 응답 파싱 실패", "image_url": image_url}
    except Exception as e:
        return {"error": f"AI 식별 오류: {str(e)}", "image_url": image_url}

    identified_name = result.get("identified_name", "")
    db_key = None
    if identified_name:
        if identified_name in PLANT_DB:
            db_key = identified_name
        else:
            matches = [n for n in PLANT_DB if identified_name in n or n in identified_name]
            if matches:
                db_key = matches[0]

    result["known_in_db"] = db_key is not None
    result["db_key"] = db_key
    if db_key:
        result["next_step"] = f"get_plant_care_guide(plant_name='{db_key}')로 관리 가이드를 이어서 조회할 수 있습니다."

    return result
