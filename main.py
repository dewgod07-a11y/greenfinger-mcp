"""
Greenfinger (그린핑거) MCP Server for Kakao PlayMCP
클라우드 배포용 진입점 (uvicorn main:app 으로 실행)
"""

import os
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from tools.diagnosis import (
    diagnose_plant_disease,
    diagnose_plant_by_image,
    # identify_plant_by_image,  # 임시 비활성화 (Tool 개수 축소 테스트)
)
from tools.design import (
    recommend_plants,
    # design_garden_layout,  # 임시 비활성화 (Tool 개수 축소 테스트)
    get_plant_care_guide,
    # get_seasonal_tips,  # 임시 비활성화 (Tool 개수 축소 테스트)
)
# from tools.schedule import (
#     create_garden_schedule,
#     send_garden_reminder,
# )  # 임시 비활성화 (Tool 개수 축소 테스트)
from tools.pots import recommend_pot_size
# from tools.pots import diagnose_pot_condition, manage_my_pots  # 임시 비활성화
# from tools.materials import search_garden_materials  # 임시 비활성화

# ── MCP 서버 인스턴스 ─────────────────────────────────────────────
mcp = FastMCP(
    name="greenfinger-mcp",
    instructions=(
        "홈 가드닝을 위한 AI 도우미 — 식물 병해충 진단, 식물 추천, "
        "정원 레이아웃 설계, 화분 사이즈 추천·관리, 관리 일정·알림, "
        "원예 자재 안내를 제공합니다."
    ),
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
    stateless_http=True,
)


# ── Health check (PlayMCP 연결 확인용) ────────────────────────────
@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "greenfinger-mcp"})


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


# ── Tool 등록 (5개 — 배포 문제 진단을 위해 임시 축소, 원래는 13개) ──────
mcp.tool()(diagnose_plant_disease)
mcp.tool()(diagnose_plant_by_image)
mcp.tool()(recommend_plants)
mcp.tool()(get_plant_care_guide)
mcp.tool()(recommend_pot_size)

# 나머지 8개는 아래 import를 되살리고 등록만 다시 추가하면 됩니다:
# identify_plant_by_image, design_garden_layout, get_seasonal_tips,
# create_garden_schedule, send_garden_reminder,
# diagnose_pot_condition, manage_my_pots, search_garden_materials

# ── ASGI app (uvicorn main:app 으로 실행) ─────────────────────────
app = mcp.streamable_http_app()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
