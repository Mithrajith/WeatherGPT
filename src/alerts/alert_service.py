from datetime import datetime
from typing import Any, Optional, List
from sqlalchemy.orm import Session
from src.alerts.warning_parser import parse_warning
from src.alerts.alert_engine import process_warning
from src.alerts.database import Alert
from src.alerts.websocket_manager import websocket_manager
from src.alerts.schemas import AlertResponse

class AlertService:
    @staticmethod
    async def process_warning_data(
        db: Session,
        raw_data: Any,
        reference_time: Optional[datetime] = None
    ) -> AlertResponse:
        """
        Coordinates the alert warning workflow:
        1. Normalizes warning data using warning_parser.
        2. Generates alert structure and severity mappings via alert_engine.
        3. Prevents duplicates by querying the database for the external_warning_id (alert_id).
        4. Persists the alert to PostgreSQL/SQLite database if not a duplicate.
        5. Broadcasts the alert to WebSockets.
        """
        # Parse warning
        warning = parse_warning(raw_data)

        # Process alert details (maps severity and validates expiration)
        alert_response = process_warning(warning, reference_time=reference_time)

        # Check duplicate
        existing_alert = db.query(Alert).filter(Alert.external_warning_id == alert_response.alert_id).first()
        if existing_alert:
            # It's a duplicate, ignore saving and broadcasting. Return existing alert.
            return AlertResponse(
                event="weather_alert",
                alert_id=existing_alert.external_warning_id,
                district=existing_alert.district,
                severity=existing_alert.severity,
                title=existing_alert.title,
                message=existing_alert.message,
                action=existing_alert.action,
                valid_until=existing_alert.valid_until
            )

        # Save to database
        db_alert = Alert(
            external_warning_id=alert_response.alert_id,
            district=alert_response.district,
            warning_type=warning.warning_type,
            severity=alert_response.severity,
            title=alert_response.title,
            message=alert_response.message,
            action=alert_response.action,
            valid_from=warning.valid_from,
            valid_until=warning.valid_until
        )
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)

        # Broadcast payload
        alert_payload = alert_response.model_dump()
        alert_payload["valid_until"] = alert_payload["valid_until"].isoformat()
        await websocket_manager.broadcast(alert_payload)

        return alert_response

    @staticmethod
    def get_alerts_by_district(db: Session, district: str) -> List[Alert]:
        """
        Retrieves all stored alerts for a given district (case-insensitive).
        """
        return db.query(Alert).filter(Alert.district.ilike(district.strip())).all()
