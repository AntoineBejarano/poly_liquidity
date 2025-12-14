"""
Script para probar los endpoints de configuración y decision traces.
"""
import httpx
import json
import asyncio
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

async def test_health():
    """Test health endpoint."""
    print("Testing /health endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

async def test_get_config():
    """Test GET /system/config endpoint."""
    print("\nTesting GET /system/config endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/system/config?include_metadata=true", timeout=5.0)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Categories: {list(data.keys())}")
                for category, configs in data.items():
                    print(f"  {category}: {len(configs)} parameters")
            else:
                print(f"Error: {response.text}")
            return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

async def test_get_decision_traces():
    """Test GET /system/decision-traces endpoint."""
    print("\nTesting GET /system/decision-traces endpoint...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/system/decision-traces?limit=10", timeout=5.0)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Total traces: {data.get('total', 0)}")
                print(f"Returned: {len(data.get('traces', []))}")
                if data.get('traces'):
                    print(f"First trace: {data['traces'][0].get('decision_stage')} - {data['traces'][0].get('decision')}")
            else:
                print(f"Error: {response.text}")
            return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

async def main():
    print("=" * 60)
    print("Testing Backend Endpoints")
    print("=" * 60)
    
    results = []
    results.append(("Health Check", await test_health()))
    results.append(("Get Config", await test_get_config()))
    results.append(("Get Decision Traces", await test_get_decision_traces()))
    
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{name}: {status}")

if __name__ == "__main__":
    asyncio.run(main())

