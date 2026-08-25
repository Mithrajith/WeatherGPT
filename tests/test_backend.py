import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient

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

def _warning_payload(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "district": "Coimbatore",
        "warning_type": "heavy_rain",
        "severity": "orange",
        "description": "Heavy rainfall is expected in Coimbatore.",
        "valid_from": (now - timedelta(hours=1)).isoformat(),
        "valid_until": (now + timedelta(hours=12)).isoformat(),
        "external_warning_id": f"TEST-{uuid.uuid4().hex[:8].upper()}",
    }
    payload.update(overrides)
    return payload

@pytest.mark.asyncio
async def test_process_warning_creates_alert():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = _warning_payload()
        response = await ac.post("/alerts/process", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["event"] == "weather_alert"
    assert data["alert_id"] == payload["external_warning_id"]
    assert data["district"] == "Coimbatore"
    assert data["severity"] == "high"
    assert data["title"]
    assert data["action"]

@pytest.mark.asyncio
async def test_process_duplicate_warning_not_duplicated():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = _warning_payload()
        first = await ac.post("/alerts/process", json=payload)
        second = await ac.post("/alerts/process", json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["alert_id"] == second.json()["alert_id"]

@pytest.mark.asyncio
async def test_get_alerts_by_district():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = _warning_payload(district="TestDistrict")
        created = await ac.post("/alerts/process", json=payload)
        listing = await ac.get("/alerts/TestDistrict")
    assert created.status_code == 201
    assert listing.status_code == 200
    results = listing.json()
    assert isinstance(results, list)
    assert any(a["alert_id"] == payload["external_warning_id"] for a in results)

@pytest.mark.asyncio
async def test_process_invalid_warning_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/alerts/process",
            json=_warning_payload(severity="invalid_severity_level"),
        )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_get_recent_alerts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/alerts/process", json=_warning_payload(severity="orange"))
        response = await ac.get("/alerts/recent")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_crop_advisory():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/advisory",
            json={
                "district": "Coimbatore",
                "crop": "paddy",
                "rainfall": 35.0,
                "temperature": 29.0,
                "humidity": 78.0,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "paddy"
    assert data["risk_level"]
    assert isinstance(data["recommendations"], list)

def test_websocket_alert_broadcast():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/alerts") as ws:
            payload = _warning_payload(district="WsDistrict")
            resp = client.post("/alerts/process", json=payload)
            assert resp.status_code == 201
            received = ws.receive_json()
            assert received["event"] == "weather_alert"
            assert received["alert_id"] == payload["external_warning_id"]

@pytest.mark.asyncio
async def test_active_alerts_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = _warning_payload(district="ActiveDistrict")
        created = await ac.post("/alerts/process", json=payload)
        listing = await ac.get("/api/v1/alerts/active?district=ActiveDistrict")
    assert created.status_code == 201
    assert listing.status_code == 200
    results = listing.json()
    assert any(a["alert_id"] == payload["external_warning_id"] for a in results)

@pytest.mark.asyncio
async def test_current_weather_includes_active_alerts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = _warning_payload(district="Chennai")
        await ac.post("/alerts/process", json=payload)
        response = await ac.get("/api/v1/weather/current?city=Chennai&lat=13.0827&lon=80.2707")
    assert response.status_code == 200
    data = response.json()
    assert "active_alerts" in data
    assert any(a["alert_id"] == payload["external_warning_id"] for a in data["active_alerts"])

@pytest.mark.asyncio
async def test_forecast_promotes_severe_days_to_alerts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/weather/forecast?city=Forecastville&lat=11.0&lon=77.0&days=5"
        )
    assert response.status_code == 200
    data = response.json()
    assert "active_alerts" in data
    # The fallback forecast includes a thunderstorm/heavy-rain day, which must be promoted
    assert len(data["active_alerts"]) >= 1
    for alert in data["active_alerts"]:
        assert alert["district"].lower() == "forecastville"
        assert alert["alert_id"].startswith("AUTO-FORECASTVILLE-")
