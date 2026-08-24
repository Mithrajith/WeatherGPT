from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from src.alerts.schemas import WarningInput, AlertResponse, AdvisoryInput, AdvisoryResponse
from src.alerts.database import get_db
from src.alerts.alert_service import AlertService
from src.alerts.advisory_engine import get_farmer_advisory
from src.alerts.websocket_manager import websocket_manager

router = APIRouter()

@router.get("/alerts/mock-payloads")
def get_mock_payloads():
    """
    Retrieve raw JSON warning payloads representing various test cases (e.g. Yellow warning, Red warning, Expired, Invalid)
    for testing in Swagger UI.
    """
    now = datetime.now(timezone.utc)
    return {
        "1_no_warning": {
            "description": "District has no alerts",
            "search_district": "Bangalore"
        },
        "2_yellow_warning": {
            "district": "Coimbatore",
            "warning_type": "high_winds",
            "severity": "yellow",
            "description": "Moderate high winds expected in Coimbatore.",
            "valid_from": (now - timedelta(hours=1)).isoformat(),
            "valid_until": (now + timedelta(hours=23)).isoformat(),
            "external_warning_id": "MOCK-INPUT-YELLOW"
        },
        "3_orange_warning": {
            "district": "Coimbatore",
            "warning_type": "heavy_rain",
            "severity": "orange",
            "description": "Heavy rainfall is expected in Coimbatore.",
            "valid_from": (now - timedelta(hours=2)).isoformat(),
            "valid_until": (now + timedelta(hours=22)).isoformat(),
            "external_warning_id": "MOCK-INPUT-ORANGE"
        },
        "4_red_warning": {
            "district": "Coimbatore",
            "warning_type": "cyclone",
            "severity": "red",
            "description": "Severe cyclone warning for Coimbatore.",
            "valid_from": (now - timedelta(hours=3)).isoformat(),
            "valid_until": (now + timedelta(hours=21)).isoformat(),
            "external_warning_id": "MOCK-INPUT-RED"
        },
        "5_duplicate_warning": {
            "district": "Coimbatore",
            "warning_type": "heavy_rain",
            "severity": "orange",
            "description": "Heavy rainfall is expected in Coimbatore.",
            "valid_from": (now - timedelta(hours=2)).isoformat(),
            "valid_until": (now + timedelta(hours=22)).isoformat(),
            "external_warning_id": "MOCK-INPUT-ORANGE"
        },
        "6_different_district": {
            "district": "Chennai",
            "warning_type": "heavy_rain",
            "severity": "yellow",
            "description": "Light rain expected in Chennai.",
            "valid_from": (now - timedelta(hours=1)).isoformat(),
            "valid_until": (now + timedelta(hours=12)).isoformat(),
            "external_warning_id": "MOCK-INPUT-CHENNAI"
        },
        "7_expired_warning": {
            "district": "Coimbatore",
            "warning_type": "heatwave",
            "severity": "orange",
            "description": "Extreme heat in Coimbatore.",
            "valid_from": (now - timedelta(days=2)).isoformat(),
            "valid_until": (now - timedelta(days=1)).isoformat(),
            "external_warning_id": "MOCK-INPUT-EXPIRED"
        },
        "8_invalid_warning": {
            "district": "",
            "warning_type": "heavy_rain",
            "severity": "invalid_severity_level",
            "description": "Invalid format warning",
            "valid_from": "invalid_date",
            "valid_until": "invalid_date"
        }
    }

@router.get("/alerts/{district}", response_model=List[AlertResponse])
def get_alerts_by_district(district: str, db: Session = Depends(get_db)):
    """
    Retrieve stored alerts for a given district.
    """
    alerts = AlertService.get_alerts_by_district(db, district)
    return [
        AlertResponse(
            event="weather_alert",
            alert_id=a.external_warning_id,
            district=a.district,
            severity=a.severity,
            title=a.title,
            message=a.message,
            action=a.action,
            valid_until=a.valid_until
        )
        for a in alerts
    ]

@router.post("/alerts/process", response_model=AlertResponse, status_code=201)
async def process_warning_route(warning_data: WarningInput, db: Session = Depends(get_db)):
    """
    Process incoming warning data, save if not duplicate, and broadcast to subscribers.
    """
    try:
        alert = await AlertService.process_warning_data(db, warning_data)
        return alert
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/advisory", response_model=AdvisoryResponse)
def get_crop_advisory_route(advisory_in: AdvisoryInput):
    """
    Compute farming recommendations for a given district, crop, and weather conditions.
    """
    try:
        advisory = get_farmer_advisory(
            district=advisory_in.district,
            crop=advisory_in.crop,
            rainfall=advisory_in.rainfall,
            temperature=advisory_in.temperature,
            humidity=advisory_in.humidity
        )
        return AdvisoryResponse(**advisory)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

async def handle_ws_session(websocket: WebSocket, district: Optional[str] = None):
    await websocket_manager.connect(websocket, district)
    try:
        while True:
            # Keep connection open and check for disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
    except Exception:
        await websocket_manager.disconnect(websocket)

@router.websocket("/alerts/ws")
async def websocket_alerts_legacy(websocket: WebSocket, district: Optional[str] = None):
    """
    WebSocket endpoint for legacy/alternative WS path clients.
    """
    await handle_ws_session(websocket, district)

@router.websocket("/ws/alerts")
async def websocket_alerts_standard(websocket: WebSocket, district: Optional[str] = None):
    """
    WebSocket endpoint for standard/new WS path clients.
    """
    await handle_ws_session(websocket, district)
