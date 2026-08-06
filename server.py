"""
🌱 그린핑거 MCP 서버 (Greenfinger MCP Server)
카카오 PlayMCP 등록용 메인 서버 파일 (로컬 stdio 실행용)

실행 방법:
  pip install -r requirements.txt
  python server.py
"""

from mcp.server.fastmcp import FastMCP
from tools.diagnosis import (
    diagnose_plant_disease,
    diagnose_plant_by_image,
    identify_plant_by_image,
)
from tools.design import (
    recommend_plants,
    design_garden_layout,
    get_plant_care_guide,
    get_seasonal_tips,
)
from tools.schedule import (
    create_garden_schedule,
    send_garden_reminder,
)
from tools.pots import recommend_pot_size, diagnose_pot_condition, manage_my_pots
from tools.materials import search_garden_materials

# ── MCP 서버 인스턴스 생성 ─────────────────────────────────────
mcp = FastMCP(
    name="그린핑거 MCP",
    instructions=(
        "식물 병해충 진단, 식물 추천, 정원 레이아웃 설계, 화분 사이즈 추천·관리, "
        "관리 일정·알림, 원예 자재 안내까지 — 홈가드닝을 지키는 AI 도구 모음입니다."
    ),
)

# ── 카테고리별 Tool 등록 ───────────────────────────────────────
# 🔬 병해충 진단·식별 (3개)
mcp.tool()(diagnose_plant_disease)
mcp.tool()(diagnose_plant_by_image)
mcp.tool()(identify_plant_by_image)

# 🌱 식물 추천·정원 설계·관리 가이드 (4개)
mcp.tool()(recommend_plants)
mcp.tool()(design_garden_layout)
mcp.tool()(get_plant_care_guide)
mcp.tool()(get_seasonal_tips)

# 📅 관리 일정·알림 (2개)
mcp.tool()(create_garden_schedule)
mcp.tool()(send_garden_reminder)

# 🪴 화분 관리 (3개)
mcp.tool()(recommend_pot_size)
mcp.tool()(diagnose_pot_condition)
mcp.tool()(manage_my_pots)

# 🧰 원예 자재 안내 (1개)
mcp.tool()(search_garden_materials)


# ── 실행 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    # 로컬 테스트: stdio 모드
    # 클라우드 배포: main.py의 streamable-http 앱 사용
    mcp.run(transport="stdio")
