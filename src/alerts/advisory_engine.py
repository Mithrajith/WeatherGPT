from typing import Dict, Any, List

VALID_CROPS = {"paddy", "cotton", "maize", "groundnut", "wheat"}

def get_farmer_advisory(
    district: str,
    crop: str,
    rainfall: float,
    temperature: float,
    humidity: float
) -> Dict[str, Any]:
    """
    Generates rule-based farmer advisory recommendations.
    Raises ValueError on unknown crop or invalid parameters.
    """
    if not district or not district.strip():
        raise ValueError("District cannot be empty")

    c = crop.lower().strip()
    if c not in VALID_CROPS:
        raise ValueError(f"Unknown crop: {crop}. Valid crops are: {', '.join(sorted(list(VALID_CROPS)))}")

    if rainfall < 0:
        raise ValueError("Rainfall cannot be negative")
    if temperature < -50 or temperature > 100:
        raise ValueError("Temperature must be between -50 and 100")
    if humidity < 0 or humidity > 100:
        raise ValueError("Humidity must be between 0 and 100")

    recommendations = []

    # Rain rules
    if rainfall > 50:
        recommendations.append("Avoid pesticide spraying before rainfall")
        recommendations.append("Monitor field drainage")
        if c == "paddy":
            recommendations.append("Postpone irrigation")
        elif c in ("cotton", "maize", "groundnut"):
            recommendations.append("Provide drainage channels to prevent waterlogging")
    elif temperature > 38 and rainfall < 5:
        recommendations.append("Increase irrigation monitoring")
        recommendations.append("Apply mulching to conserve soil moisture")

    # Humidity rules
    if humidity > 85:
        recommendations.append("Monitor for fungal diseases and pests")
        recommendations.append("Ensure proper aeration in fields")

    # Wheat specific cold rule
    if c == "wheat" and temperature < 5:
        recommendations.append("Light irrigation to protect crop from frost")

    # Fallback recommendations
    if not recommendations:
        recommendations.append("Continue regular field operations")
        recommendations.append("Monitor weather forecast for updates")

    # Risk level assessment
    if rainfall > 50 or temperature > 40 or temperature < 5:
        risk_level = "high"
    elif rainfall > 20 or temperature > 35 or humidity > 85:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "crop": c,
        "risk_level": risk_level,
        "recommendations": recommendations
    }
