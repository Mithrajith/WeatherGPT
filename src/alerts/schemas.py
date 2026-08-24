from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

class WarningInput(BaseModel):
    district: str
    warning_type: str
    severity: str
    description: str
    valid_from: str
    valid_until: str
    external_warning_id: Optional[str] = None

class NormalizedWarning(BaseModel):
    district: str
    warning_type: str
    severity: str  # must be 'green', 'yellow', 'orange', 'red'
    description: str
    valid_from: datetime
    valid_until: datetime
    external_warning_id: Optional[str] = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        sev = v.lower().strip()
        if sev not in {"green", "yellow", "orange", "red"}:
            raise ValueError(f"Invalid severity: {v}. Must be one of green, yellow, orange, red.")
        return sev

class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event: str = "weather_alert"
    alert_id: str
    district: str
    severity: str  # mapped to 'informational', 'low', 'high', 'critical'
    title: str
    message: str
    action: str
    valid_until: datetime

class AdvisoryInput(BaseModel):
    district: str
    crop: str
    rainfall: float
    temperature: float
    humidity: float

class AdvisoryResponse(BaseModel):
    crop: str
    risk_level: str
    recommendations: List[str]
