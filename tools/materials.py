"""
tools/materials.py
카테고리 5: 원예 자재 안내 Tool (1개)
  - search_garden_materials (T10)
"""
from __future__ import annotations
from data.plant_db import MATERIALS_DB


async def search_garden_materials(
    category: str = "",
    keyword: str = "",
) -> dict:
    """
    토양·비료·화분·도구 등 원예 자재 정보와 선택 기준을 자체 DB에서 안내합니다.

    Args:
        category: 자재 분류 (상토/비료/화분/도구/병충해방제용품, 미입력 시 전체)
        keyword:  자재명 또는 용도 검색어 (예: 다육, 텃밭, 흰가루병)
    """
    categories = [category] if category and category in MATERIALS_DB else list(MATERIALS_DB.keys())

    results = {}
    for cat in categories:
        entry = MATERIALS_DB[cat]
        types = entry["types"]
        if keyword:
            types = [
                t for t in types
                if keyword in t["name"] or keyword in t["use_case"] or keyword in t["criteria"]
            ]
        if types:
            results[cat] = {"types": types, "selection_tip": entry["selection_tip"]}

    total = sum(len(v["types"]) for v in results.values())
    return {
        "query": {"category": category, "keyword": keyword},
        "total_count": total,
        "materials": results,
        "message": (
            f"조건에 맞는 자재 {total}건을 찾았습니다."
            if total else "조건에 맞는 자재 정보가 없습니다. 카테고리나 검색어를 조정해보세요."
        ),
    }
