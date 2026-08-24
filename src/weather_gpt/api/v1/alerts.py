from typing import List
from fastapi import APIRouter, Query

from weather_gpt.schemas.weather import ActiveAlert
from weather_gpt.services.alert_bridge import get_active_alerts

router = APIRouter(prefix="/alerts", tags=["Active Alerts"])

@router.get("/active", response_model=List[ActiveAlert])
async def get_active_district_alerts(
    district: str = Query(..., description="District name to look up active alerts for")
):
    """Retrieve all non-expired weather alerts stored for the given district."""
    return await get_active_alerts(district)
