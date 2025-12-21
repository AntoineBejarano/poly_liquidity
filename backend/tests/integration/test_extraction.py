"""Script de prueba para verificar extracción de endpoints."""
from pathlib import Path
import sys

# Agregar backend al path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from tests.integration.test_frontend_backend_alignment import FrontendBackendAlignmentTest

if __name__ == "__main__":
    test = FrontendBackendAlignmentTest()
    
    print("Extrayendo endpoints del frontend...")
    frontend_endpoints = test.extract_frontend_endpoints()
    print(f"\nEncontrados {len(frontend_endpoints)} endpoints del frontend:")
    for ep in frontend_endpoints[:20]:
        print(f"  {ep['method']} {ep['path']} (from {ep['file']})")
    
    print("\nExtrayendo endpoints del backend...")
    backend_endpoints = test.extract_backend_endpoints()
    print(f"\nEncontrados {len(backend_endpoints)} endpoints del backend:")
    for method, path in list(backend_endpoints)[:20]:
        print(f"  {method} {path}")

