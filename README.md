# 🌱 그린핑거 MCP 서버

> 식물 병해충 진단·식별 · 식물 추천 · 정원 레이아웃 설계 · 화분 관리 · 관리 일정·알림 · 원예 자재 안내
> 카카오 PlayMCP 등록용 MCP 서버 (나무의사 MCP와 동일 구조 재사용)

---

## 📁 파일 구조

```
garden_doc_mcp/
│
├── server.py              ← 로컬 실행 진입점 (stdio)
├── main.py                 ← 클라우드 배포 진입점 (streamable-http, uvicorn main:app)
├── requirements.txt        ← 설치할 패키지 목록
├── .env.example             ← 환경변수 예시 (복사해서 .env로 사용)
├── Dockerfile               ← 클라우드 배포용
│
├── tools/                   ← Tool 구현 파일 5개 (Tool 13개)
│   ├── diagnosis.py         ← 🔬 병해충 진단·식별 (3개)
│   ├── design.py             ← 🌱 식물 추천·정원 설계·관리 가이드 (4개)
│   ├── schedule.py           ← 📅 관리 일정·알림 (2개, 카카오 연동)
│   ├── pots.py                ← 🪴 화분 관리 (3개, 화분 진단 포함)
│   └── materials.py          ← 🧰 원예 자재 안내 (1개)
│
├── config/
│   └── settings.py           ← 환경변수 로드 (API 키 등)
│
└── data/
    └── plant_db.py           ← 식물·화분·계절 작업·자재 자체 지식 베이스
```

---

## Tool 목록 (13개)

| # | Tool | 설명 | 연동 |
|---|------|------|------|
| 1 | `diagnose_plant_disease` | 증상 텍스트로 병해충 진단 | Claude AI |
| 2 | `diagnose_plant_by_image` | 사진 URL로 병해충 진단 (종 식별 포함) | Claude AI (Vision) |
| 3 | `identify_plant_by_image` | 사진 URL로 병해충 진단 없이 식물 종만 식별 | Claude AI (Vision) |
| 4 | `recommend_plants` | 공간·햇빛·목적 조건으로 식물 추천 | 자체 DB |
| 5 | `design_garden_layout` | 공간 조건 기반 정원 레이아웃 설계 | Claude AI |
| 6 | `get_plant_care_guide` | 식물별 물주기·햇빛·비료 가이드 | 자체 DB |
| 7 | `get_seasonal_tips` | 월별 계절 원예 작업 안내 | 자체 DB |
| 8 | `create_garden_schedule` | 관리 일정 등록(물주기는 계절별 간격 자동 반복) + 카카오 캘린더 연동 제안 | 카카오 캘린더 |
| 9 | `send_garden_reminder` | 관리 알림 메시지 + 카카오톡 발송 제안 | 카카오톡 |
| 10 | `recommend_pot_size` | 식물에 맞는 화분 재질·사이즈·분갈이 시기 추천 | 자체 DB |
| 11 | `diagnose_pot_condition` | 화분 증상(뿌리 노출·배수 불량 등) 기반 분갈이 시급도 진단 | Claude AI |
| 12 | `manage_my_pots` | 내가 키우는 화분 등록/목록조회/삭제 | 자체 DB |
| 13 | `search_garden_materials` | 토양·비료·화분·도구 자재 안내 | 자체 DB |

---

## ⚡ 빠른 시작

### 1단계 — 패키지 설치
```bash
pip install -r requirements.txt
```

### 2단계 — 환경변수 확인
`.env` 파일에 이미 나무의사 MCP와 동일한 `ANTHROPIC_API_KEY`가 채워져 있어
병해충 진단·식별(1, 2, 3), 정원 설계(5), 화분 진단(11)이 바로 동작합니다. 그 외 Tool은 외부 API 키가 필요 없습니다.

### 3단계 — 로컬 실행 테스트
```bash
python server.py
```

### 4단계 — PlayMCP 등록
1. [playmcp.kakao.com](https://playmcp.kakao.com) 접속 → 카카오 계정 로그인
2. `MCP 서버 등록` 클릭 → 서버 URL 입력 (클라우드 배포 후 URL)
3. 도구함에서 `카카오 톡캘린더 MCP`, `카카오톡 나와의채팅 MCP`를 함께 활성화
   (7, 8번 Tool이 반환하는 `calendar_event_suggestion` / `chat_message_suggestion` 값을
   AI가 그대로 넘겨 호출합니다)
4. AI 채팅창에서 테스트 → "몬스테라 잎이 노랗게 변했어요" 입력

---

## ☁️ 클라우드 배포 (예시)

```bash
docker build -t greenfinger-mcp .
docker run -p 8000:8000 --env-file .env greenfinger-mcp
```

---

## 💬 테스트 대화 예시

```
"몬스테라 잎 끝이 갈색으로 마르는데 왜 그런가요?"
→ diagnose_plant_disease 자동 실행

"이 식물 사진인데 이름이 뭐예요?" (사진 URL만 제공, 증상 언급 없음)
→ identify_plant_by_image 자동 실행 (병해충 진단은 하지 않고 종만 식별)

"베란다 2평, 반양지인데 어울리는 식물 추천해줘"
→ recommend_plants 자동 실행

"3평 옥상에 텃밭형 정원 설계해줘"
→ design_garden_layout 자동 실행

"방울토마토 물주기 다음 일정으로 등록해줘"
→ care_type="물주기"이고 repeat_every_days를 지정하지 않으면 현재 계절 기준
   자체 DB(watering_interval_days)에서 간격을 자동 계산해 반복 등록

"바질 물주기 3일마다 반복 알림 걸어줘"
→ repeat_every_days=3을 직접 지정하면 자동계산 대신 그 값을 그대로 사용

"우리집 몬스테라 화분 15cm인데 분갈이 필요해?"
→ recommend_pot_size 자동 실행

"화분 배수구로 뿌리가 삐져나오고 물이 겉으로 흘러내려요"
→ diagnose_pot_condition 자동 실행 (분갈이 시급도·원인 진단)

"거실 몬스테라 화분 등록해줘"
→ manage_my_pots(action="register") 자동 실행
```

---

## 📌 참고

- 나무의사 MCP(`tree_doctor_mcp`)와 동일한 아키텍처(FastMCP + Claude API + tools/config/data 구조)를
  재사용해 구현했습니다.
- 식물·화분·계절·자재 정보는 자체 DB(`data/plant_db.py`)로 구축해 외부 API 의존을 최소화했습니다.
- 조경업체 검색(카카오맵 연동) 기능은 제외했습니다 — 홈가드닝(화분·베란다·실내) 중심으로 범위를 좁혔습니다.
- 물주기는 고정 주기만으로는 정확할 수 없다는 한계를 인정하고, 계절별 자동 간격 추천 + "고정
  알림은 참고용, 흙 상태를 먼저 확인" 문구를 항상 포함해 과습·건조 오판 위험을 줄였습니다.
  (사진으로 실제 토양 수분을 판별하는 방식은 조명·표면 흙만 보이는 한계로 채택하지 않았습니다.)
