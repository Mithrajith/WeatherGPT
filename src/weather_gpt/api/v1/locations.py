from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from weather_gpt.db.session import get_db
from weather_gpt.models.location import Location
from weather_gpt.schemas.location import LocationCreate, LocationResponse

router = APIRouter(prefix="/locations", tags=["Locations"])

@router.get("/", response_model=List[LocationResponse])
async def list_locations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Location).offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    location_in: LocationCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check if duplicate location exists
    result = await db.execute(
        select(Location).where(
            Location.name == location_in.name,
            Location.state == location_in.state
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location with this name and state already exists."
        )

    new_location = Location(**location_in.model_dump())
    db.add(new_location)
    await db.commit()
    await db.refresh(new_location)
    return new_location

@router.get("/search", response_model=List[LocationResponse])
async def search_locations(
    q: str,
    db: AsyncSession = Depends(get_db)
):
    pattern = f"%{q}%"
    result = await db.execute(
        select(Location).where(
            or_(
                Location.name.ilike(pattern),
                Location.state.ilike(pattern),
                Location.pin_code.ilike(pattern)
            )
        ).limit(20)
    )
    return result.scalars().all()
