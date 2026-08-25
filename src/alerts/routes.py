from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from src.alerts.schemas import WarningInput, AlertResponse, AdvisoryInput, AdvisoryResponse
from src.alerts.database import get_db
from src.alerts.alert_service import AlertService
from src.alerts.advisory_engine import get_farmer_advisory
from src.alerts.websocket_manager import websocket_manager

router = APIRouter()

@router.get("/alerts/recent", response_model=List[AlertResponse])
def get_recent_alerts(limit: int = 50, db: Session = Depends(get_db)):
    """
    Retrieve non-expired alerts across all districts, most urgent first, for
    the Alerts page. Ordered by severity (red > orange > yellow) then by how
    soon the warning expires.
    """
    severity_rank = {"red": 0, "orange": 1, "yellow": 2}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    from src.alerts.database import Alert as AlertModel

    rows = (
        db.query(AlertModel)
        .filter(AlertModel.valid_until > now)
        .order_by(AlertModel.valid_until.asc())
        .limit(max(1, min(limit, 200)))
        .all()
    )
    rows.sort(key=lambda a: severity_rank.get((a.severity or "").lower(), 3))
    return [
        AlertResponse(
            event="weather_alert",
            alert_id=a.external_warning_id,
            district=a.district,
            severity=a.severity,
            title=a.title,
            message=a.message,
            action=a.action,
            valid_until=a.valid_until,
        )
        for a in rows
    ]

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
