import sys
import json
import httpx
from datetime import datetime, timezone

# We will try to test against the running live server first.
# If it is not running, we fall back to FastAPI TestClient for an offline demo.
BASE_URL = "http://127.0.0.1:8809"

print("==============================================================")
print("WeatherGPT Alerts & Advisory - Live Client Test Script")
print("==============================================================")

is_live = False
try:
    # Quick health check to see if the server is running on port 8000
    response = httpx.get(f"{BASE_URL}/openapi.json", timeout=2.0)
    if response.status_code == 200:
        is_live = True
        print(f"[*] Detected running server on {BASE_URL}. Testing LIVE server.")
except Exception:
    pass

client_runner = None
if not is_live:
    print("[!] No server running on port 8000. Falling back to OFFLINE TestClient.")
    try:
        from fastapi.testclient import TestClient
        from main import app
        client_runner = TestClient(app)
        print("[*] Successfully initialized offline TestClient.")
    except ImportError as e:
        print(f"[E] Failed to import application for offline testing: {e}")
        print("[*] Please start the application using: uv run uvicorn main:app --reload")
        sys.exit(1)

def make_request(method: str, path: str, json_data: dict = None):
    """
    Helper to send requests to either the live server or the offline TestClient.
    """
    if is_live:
        url = f"{BASE_URL}{path}"
        if method == "GET":
            return httpx.get(url)
        elif method == "POST":
            return httpx.post(url, json=json_data)
    else:
        if method == "GET":
            return client_runner.get(path)
        elif method == "POST":
            return client_runner.post(path, json=json_data)

# ==========================================
# STEP 1: Fetch mock data warning payloads
# ==========================================
print("\n[1] Fetching mock warning payloads from metadata API...")
try:
    response = make_request("GET", "/alerts/mock-payloads")
    assert response.status_code == 200, f"Failed: {response.text}"
    mock_payloads = response.json()
    print("✓ Successfully retrieved mock warning payloads.")
except Exception as e:
    print(f"[E] Error fetching payloads: {e}")
    sys.exit(1)

# ==========================================
# STEP 2: Process mock warnings
# ==========================================
print("\n[2] Submitting mock warnings to POST /alerts/process...")
results = {}

for case_name, payload in mock_payloads.items():
    if case_name == "1_no_warning":
        print(f"\n---> Case 1: No Warning (Search for {payload['search_district']})")
        res = make_request("GET", f"/alerts/{payload['search_district']}")
        print(f"     GET /alerts/{payload['search_district']} -> Code {res.status_code}")
        print(f"     Response: {json.dumps(res.json(), indent=2)}")
        continue

    print(f"\n---> Case: {case_name}")
    print(f"     Submitting warning for district '{payload.get('district')}', severity '{payload.get('severity')}'")
    
    res = make_request("POST", "/alerts/process", payload)
    print(f"     POST /alerts/process -> Code {res.status_code}")
    
    if res.status_code == 201:
        alert = res.json()
        print(f"     ✓ Saved and Mapped Alert:")
        print(f"       Alert ID: {alert['alert_id']}")
        print(f"       Mapped Severity: {alert['severity']}")
        print(f"       Action Required: {alert['action']}")
    else:
        print(f"     ✗ Rejected (Expected for invalid/expired warnings):")
        print(f"       Detail: {res.json().get('detail', res.text)}")

# ==========================================
# STEP 3: Retrieve current active alerts
# ==========================================
print("\n[3] Querying stored alerts for Coimbatore...")
res = make_request("GET", "/alerts/Coimbatore")
print(f"    GET /alerts/Coimbatore -> Code {res.status_code}")
print(json.dumps(res.json(), indent=2))

# ==========================================
# STEP 4: Request Farmer Advisory Recommendations
# ==========================================
print("\n[4] Requesting farmer agricultural advisories...")

advisory_tests = [
    {
        "district": "Coimbatore",
        "crop": "paddy",
        "rainfall": 65.5,
        "temperature": 27.5,
        "humidity": 92.0
    },
    {
        "district": "Coimbatore",
        "crop": "cotton",
        "rainfall": 2.0,
        "temperature": 41.5,
        "humidity": 45.0
    },
    {
        "district": "Coimbatore",
        "crop": "wheat",
        "rainfall": 0.0,
        "temperature": 3.0,
        "humidity": 75.0
    },
    {
        "district": "Coimbatore",
        "crop": "banana",  # Unknown crop
        "rainfall": 5.0,
        "temperature": 25.0,
        "humidity": 60.0
    }
]

for test in advisory_tests:
    print(f"\n---> Querying advisory for crop '{test['crop']}' in '{test['district']}'")
    res = make_request("POST", "/advisory", test)
    print(f"     POST /advisory -> Code {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print(f"     ✓ Advisory Details:")
        print(f"       Risk Level: {data['risk_level'].upper()}")
        print(f"       Recommendations:")
        for r in data["recommendations"]:
            print(f"         - {r}")
    else:
        print(f"     ✗ Error: {res.json().get('detail', res.text)}")

print("\n==============================================================")
print("Client test script completed successfully.")
print("==============================================================")
