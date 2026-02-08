"""
Test aislado de conexión a Gamma API (Polymarket).
Ejecutar desde backend: python test_gamma_connection.py
"""
import os
import sys

# Evitar que el script use proxy de entorno para la prueba
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    print(f"  {k} = {os.environ.get(k, '(no set)')}")

BASE = "https://gamma-api.polymarket.com"
URL = f"{BASE}/events?closed=false&limit=1"

print("\n--- 1) httpx con trust_env=False ---")
try:
    import httpx
    with httpx.Client(timeout=15.0, trust_env=False) as client:
        r = client.get(URL)
        print(f"  status={r.status_code}, len={len(r.content)}")
        if r.status_code == 200:
            print("  OK: Conexión directa funciona con trust_env=False")
        else:
            print(f"  body (first 200 chars): {r.text[:200]}")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n--- 2) httpx con trust_env=True (usa proxy si está definido) ---")
try:
    with httpx.Client(timeout=15.0, trust_env=True) as client:
        r = client.get(URL)
        print(f"  status={r.status_code}, len={len(r.content)}")
        if r.status_code == 200:
            print("  OK: Conexión con trust_env=True también funciona")
        else:
            print(f"  body (first 200 chars): {r.text[:200]}")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n--- 3) urllib.request (sin httpx) ---")
try:
    import urllib.request
    req = urllib.request.Request(URL, headers={"User-Agent": "PolyLiquidity-Test/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
        print(f"  status=200, len={len(data)}")
        print("  OK: urllib puede conectar")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")

print("\n--- Done ---")
