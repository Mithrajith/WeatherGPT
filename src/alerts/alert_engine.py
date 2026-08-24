import hashlib
from datetime import datetime, timezone
from typing import Optional
from src.alerts.schemas import NormalizedWarning, AlertResponse

SEVERITY_MAPPING = {
    "green": "informational",
    "yellow": "low",
    "orange": "high",
    "red": "critical",
}

def get_action_for_warning(warning_type: str, severity: str) -> str:
    """
    Returns a standard actionable recommendation based on the warning type and severity.
    """
    wt = warning_type.lower().strip()
    sev = severity.lower().strip()
    
    if "rain" in wt or "flood" in wt or "thunderstorm" in wt:
        if sev in ("orange", "red", "high", "critical"):
            return "Avoid low-lying areas and unnecessary travel."
        else:
            return "Keep an umbrella handy and avoid waterlogged streets."
    elif "heat" in wt or "temp" in wt:
        return "Stay indoors, keep hydrated, and avoid direct sunlight during peak hours."
    elif "cyclone" in wt or "wind" in wt or "storm" in wt:
        return "Stay indoors, secure loose outdoor objects, and follow official evacuation orders."
    
    return "Stay tuned to weather updates and exercise caution."

def process_warning(warning: NormalizedWarning, reference_time: Optional[datetime] = None) -> AlertResponse:
    """
    Determines whether a warning should become an alert.
    Raises ValueError if the warning is expired.
    """
    ref = reference_time or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)

    # Check if expired
    if warning.valid_until < ref:
        raise ValueError("Warning has expired")

    # Map severity
    severity_mapped = SEVERITY_MAPPING.get(warning.severity, "informational")

    # Generate deterministic alert_id if no external_warning_id is provided
    if warning.external_warning_id:
        alert_id = warning.external_warning_id
    else:
        # Create unique representation of core fields
        unique_str = f"{warning.district}:{warning.warning_type}:{warning.severity}:{warning.valid_from.isoformat()}:{warning.valid_until.isoformat()}"
        alert_hash = hashlib.md5(unique_str.encode("utf-8")).hexdigest()[:8].upper()
        alert_id = f"ALT-{alert_hash}"

    title = f"{warning.warning_type.replace('_', ' ').title()} Warning"
    
    # Message fallback if description is empty
    message = warning.description.strip()
    if not message:
        message = f"{title} in effect for {warning.district}."

    action = get_action_for_warning(warning.warning_type, warning.severity)

    return AlertResponse(
        event="weather_alert",
        alert_id=alert_id,
        district=warning.district,
        severity=severity_mapped,
        title=title,
        message=message,
        action=action,
        valid_until=warning.valid_until
    )
