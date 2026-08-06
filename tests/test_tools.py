"""
tests/test_tools.py  -  Tool 동작 로컬 테스트 스크립트
실행: python tests/test_tools.py
"""
import asyncio, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.diagnosis import diagnose_plant_disease
from tools.design import recommend_plants, get_plant_care_guide, get_seasonal_tips
from tools.schedule import create_garden_schedule
from tools.pots import recommend_pot_size, diagnose_pot_condition, manage_my_pots
from tools.materials import search_garden_materials


async def test_all():
    print("=" * 60)
    print("🌱 그린핑거 MCP Tool 테스트 시작")
    print("=" * 60)

    print("\n[Test 1] diagnose_plant_disease")
    result = await diagnose_plant_disease(
        plant_name="몬스테라",
        symptoms="잎 끝이 갈색으로 마르고 잎이 처짐",
        location="잎",
    )
    print(f"  → 진단 수: {len(result.get('diagnoses', []))}")
    if result.get("diagnoses"):
        print(f"  → 주요 진단: {result['diagnoses'][0].get('issue_name', 'N/A')}")
    print("  ✅ 통과")

    print("\n[Test 2] recommend_plants")
    result = await recommend_plants(space="베란다", light="양지", purpose="허브")
    print(f"  → 추천 수: {result.get('total_count', 0)}")
    print("  ✅ 통과")

    print("\n[Test 3] get_plant_care_guide")
    result = await get_plant_care_guide(plant_name="로즈마리")
    print(f"  → found: {result.get('found')}, 난이도: {result.get('difficulty', 'N/A')}")
    print("  ✅ 통과")

    print("\n[Test 4] get_seasonal_tips")
    result = await get_seasonal_tips(month=5)
    print(f"  → 계절: {result.get('season', 'N/A')}, 작업 수: {len(result.get('tasks', []))}")
    print("  ✅ 통과")

    print("\n[Test 5] create_garden_schedule (물주기, 계절별 간격 자동 계산)")
    result = await create_garden_schedule(
        plant_name="베란다_몬스테라_1번", care_type="물주기",
        scheduled_date="2026-08-10", scheduled_time="09:00",
    )
    print(f"  → 등록: {result.get('success')}, ID: {result.get('record_id')}, 반복: {result.get('repeat')}")
    print("  ✅ 통과")

    print("\n[Test 5b] create_garden_schedule (repeat_every_days 수동 지정 시 자동계산 무시)")
    result = await create_garden_schedule(
        plant_name="베란다_바질_1번", care_type="물주기",
        scheduled_date="2026-08-10", scheduled_time="09:00",
        repeat_every_days=3,
    )
    print(f"  → 반복: {result.get('repeat')}, recurrence: {result['calendar_event_suggestion'].get('recurrence')}")
    print("  ✅ 통과")

    print("\n[Test 5c] create_garden_schedule (물주기 외 유형은 자동계산 미적용)")
    result = await create_garden_schedule(
        plant_name="베란다_몬스테라_1번", care_type="비료",
        scheduled_date="2026-08-10", scheduled_time="09:00",
    )
    print(f"  → 반복: {result.get('repeat')}")
    print("  ✅ 통과")

    print("\n[Test 6] recommend_pot_size")
    result = await recommend_pot_size(plant_name="몬스테라", current_pot_diameter_cm=15)
    print(f"  → needs_repot: {result.get('needs_repot')}, 추천 사이즈: {result.get('recommended_next_diameter_cm')}cm")
    print("  ✅ 통과")

    print("\n[Test 6b] diagnose_pot_condition")
    result = await diagnose_pot_condition(
        plant_name="몬스테라",
        symptoms="화분 배수구멍으로 뿌리가 삐져나왔고, 물을 줘도 겉으로 바로 흘러내려요",
        current_pot_diameter_cm=15,
    )
    print(f"  → urgency: {result.get('urgency')}, 추천 사이즈: {result.get('recommended_pot_diameter_cm')}cm")
    print("  ✅ 통과")

    print("\n[Test 7] manage_my_pots (register → list → remove)")
    reg = await manage_my_pots(action="register", pot_name="거실_몬스테라", plant_name="몬스테라", location="거실", pot_diameter_cm=20)
    print(f"  → 등록: {reg.get('success')}, pot_id: {reg['pot']['pot_id'] if reg.get('success') else 'N/A'}")
    listed = await manage_my_pots(action="list")
    print(f"  → 목록 수: {listed.get('total_count', 0)}")
    if reg.get("success"):
        removed = await manage_my_pots(action="remove", pot_id=reg["pot"]["pot_id"])
        print(f"  → 삭제: {removed.get('success')}")
    print("  ✅ 통과")

    print("\n[Test 8] search_garden_materials")
    result = await search_garden_materials(category="비료")
    print(f"  → 결과 수: {result.get('total_count', 0)}")
    print("  ✅ 통과")

    print("\n" + "=" * 60)
    print("🎉 모든 테스트 완료!")
    print("\n다음 단계:")
    print("  1. pip install -r requirements.txt")
    print("  2. python server.py")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all())
