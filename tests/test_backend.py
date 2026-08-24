import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from weather_gpt.main import app
from weather_gpt.db.session import init_db
from weather_gpt.services.imd_service import imd_client
from weather_gpt.services.cache_service import cache_service

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_imd_current_weather():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/weather/current?city=Chennai&lat=13.0827&lon=80.2707")
    assert response.status_code == 200
    data = response.json()
    assert data["location"] == "Chennai"
    assert "temperature" in data
    assert "humidity" in data

@pytest.mark.asyncio
async def test_imd_forecast():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/weather/forecast?city=Bengaluru&lat=12.9716&lon=77.5946&days=3")
    assert response.status_code == 200
    data = response.json()
    assert data["location"] == "Bengaluru"
    assert len(data["forecast"]) == 3

@pytest.mark.asyncio
async def test_cache_service():
    await cache_service.set("test_key", {"temp": 25.0})
    val = await cache_service.get("test_key")
    assert val == {"temp": 25.0}
