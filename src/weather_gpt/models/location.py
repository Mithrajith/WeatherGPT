from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from weather_gpt.db.base import Base
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from weather_gpt.models.historical_weather import HistoricalWeather

class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    pin_code: Mapped[str] = mapped_column(String(20), index=True, nullable=True)

    historical_records: Mapped[List["HistoricalWeather"]] = relationship("HistoricalWeather", back_populates="location", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Location(id={self.id}, name='{self.name}', state='{self.state}')>"

