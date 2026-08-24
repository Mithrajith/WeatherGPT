from datetime import datetime, timezone
from typing import Any, Dict
from src.alerts.schemas import NormalizedWarning

def parse_warning(data: Any) -> NormalizedWarning:
    """
    Parses and normalizes raw warning data.
    data can be a dictionary or a Pydantic model.
    """
    if not isinstance(data, dict):
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        elif hasattr(data, "dict"):
            data = data.dict()
        elif hasattr(data, "__dict__"):
            data = data.__dict__
        else:
            raise ValueError("Input data must be a dictionary or a Pydantic model")

    # Validate mandatory fields
    required_fields = ["district", "warning_type", "severity", "description", "valid_from", "valid_until"]
    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValueError(f"Missing required field: {field}")
        
    district = str(data["district"]).strip()
    if not district:
        raise ValueError("District name cannot be empty")
    
    warning_type = str(data["warning_type"]).strip().lower()
    if not warning_type:
        raise ValueError("Warning type cannot be empty")
        
    severity = str(data["severity"]).strip().lower()
    if not severity:
        raise ValueError("Severity cannot be empty")
        
    description = str(data["description"]).strip()
    
    # Parse datetimes and normalize to UTC
    def parse_dt(dt_val: Any, field_name: str) -> datetime:
        if isinstance(dt_val, datetime):
            dt = dt_val
        elif isinstance(dt_val, str):
            try:
                # Remove Z and replace with +00:00 for fromisoformat if needed
                val = dt_val
                if val.endswith("Z"):
                    val = val[:-1] + "+00:00"
                dt = datetime.fromisoformat(val)
            except ValueError as e:
                raise ValueError(f"Invalid datetime format for {field_name}: {dt_val}") from e
        else:
            raise ValueError(f"Unsupported datetime type for {field_name}: {type(dt_val)}")
            
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    valid_from = parse_dt(data["valid_from"], "valid_from")
    valid_until = parse_dt(data["valid_until"], "valid_until")

    if valid_until <= valid_from:
        raise ValueError("valid_until must be after valid_from")

    external_warning_id = data.get("external_warning_id")
    if external_warning_id is not None:
        external_warning_id = str(external_warning_id).strip()
        if not external_warning_id:
            external_warning_id = None

    # Let Pydantic validate severity limits and types
    return NormalizedWarning(
        district=district.title(),
        warning_type=warning_type,
        severity=severity,
        description=description,
        valid_from=valid_from,
        valid_until=valid_until,
        external_warning_id=external_warning_id
    )
