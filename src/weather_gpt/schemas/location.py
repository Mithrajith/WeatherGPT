from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class LocationBase(BaseModel):
    name: str
    state: str
    country: str = "India"
    latitude: float
    longitude: float
    pin_code: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

