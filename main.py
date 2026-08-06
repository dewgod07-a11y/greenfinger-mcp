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


# ── Tool 등록 (13개) ───────────────────────────────────────────────
# 🔬 병해충 진단·식별 (3개)
mcp.tool()(diagnose_plant_disease)
mcp.tool()(diagnose_plant_by_image)
mcp.tool()(identify_plant_by_image)

# 🌱 식물 추천·정원 설계·관리 가이드 (4개)
mcp.tool()(recommend_plants)
mcp.tool()(design_garden_layout)
mcp.tool()(get_plant_care_guide)
mcp.tool()(get_seasonal_tips)

# 📅 관리 일정·알림 (2개, 카카오 연동)
mcp.tool()(create_garden_schedule)
mcp.tool()(send_garden_reminder)

# 🪴 화분 관리 (3개)
mcp.tool()(recommend_pot_size)
mcp.tool()(diagnose_pot_condition)
mcp.tool()(manage_my_pots)

# 🧰 원예 자재 안내 (1개)
mcp.tool()(search_garden_materials)

# ── ASGI app (uvicorn main:app 으로 실행) ─────────────────────────
app = mcp.streamable_http_app()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
