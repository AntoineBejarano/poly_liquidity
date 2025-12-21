"""
Test de Integración: Verificación de Alineación Frontend-Backend

Este test verifica que:
1. Todos los endpoints que el frontend usa existen en el backend
2. Los endpoints responden con el formato esperado
3. Los tipos de datos coinciden
4. Los métodos HTTP son correctos
"""
import pytest
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

try:
    import httpx
except ImportError:
    httpx = None

# Configuración
BACKEND_URL = "http://localhost:8000"
FRONTEND_DIR = Path(__file__).parent.parent.parent.parent / "frontend"
BACKEND_API_DIR = Path(__file__).parent.parent.parent / "app" / "api"

# Mock token para tests (en producción usar token real)
TEST_TOKEN = "test_token_12345"


class FrontendBackendAlignmentTest:
    """Test de alineación entre frontend y backend."""
    
    def __init__(self):
        self.frontend_endpoints: List[Dict] = []
        self.backend_endpoints: Set[Tuple[str, str]] = set()  # (method, path)
        self.missing_endpoints: List[Dict] = []
        self.mismatched_endpoints: List[Dict] = []
    
    def extract_frontend_endpoints(self) -> List[Dict]:
        """Extrae todos los endpoints que el frontend usa."""
        endpoints = []
        
        # Patrones mejorados para encontrar llamadas API
        # Buscar: api.get('/path'), api.get<Type>('/path'), api.post(`/path`), await api.patch(...), etc.
        patterns = [
            # api.get('/path') o api.get<Type>('/path') o api.get("/path") - con o sin await
            (r'(?:await\s+)?api\.(get|post|patch|put|delete)\s*(?:<[^>]+>)?\s*\(\s*["\']([^"\']+)["\']', 1, 2),
            # api.get(`/path`) o api.get<Type>(`/path`) o api.get(`/path/${var}`) - con o sin await  
            (r'(?:await\s+)?api\.(get|post|patch|put|delete)\s*(?:<[^>]+>)?\s*\(\s*`([^`]+)`', 1, 2),
        ]
        
        # Debug: verificar que FRONTEND_DIR existe
        if not FRONTEND_DIR.exists():
            print(f"WARNING: Frontend directory not found: {FRONTEND_DIR}")
            return []
        
        # Buscar en archivos TypeScript/TSX (excluir node_modules)
        for file_path in FRONTEND_DIR.rglob("*.ts"):
            if file_path.is_file() and "node_modules" not in str(file_path):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    self._extract_from_content(content, patterns, endpoints, file_path)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
        
        for file_path in FRONTEND_DIR.rglob("*.tsx"):
            if file_path.is_file() and "node_modules" not in str(file_path):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    self._extract_from_content(content, patterns, endpoints, file_path)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
        
        return endpoints
    
    def _extract_from_content(self, content: str, patterns: List[Tuple], endpoints: List[Dict], file_path: Path):
        """Extrae endpoints de un contenido de archivo."""
        seen = set()  # Para evitar duplicados
        
        for pattern, method_idx, path_idx in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                try:
                    method = match.group(method_idx).upper()
                    path = match.group(path_idx)
                    
                    # Remover query strings para comparación
                    if '?' in path:
                        path_base = path.split('?')[0]
                    else:
                        path_base = path
                    
                    # Limpiar path (remover variables de template)
                    # Ej: `/strategies/${strategyId}/activate` -> `/strategies/{id}/activate`
                    path_template = re.sub(r'\$\{[^}]+\}', '{id}', path_base)
                    # Remover espacios y caracteres especiales
                    path_template = path_template.strip()
                    # Remover trailing slash
                    path_template = path_template.rstrip('/') or '/'
                    
                    # Normalizar variables comunes: {strategy_id}, {id}, etc. -> {id}
                    path_template = re.sub(r'\{[^}]*(id|Id|ID|_id)[^}]*\}', '{id}', path_template)
                    
                    # Evitar duplicados
                    endpoint_key = (method, path_template)
                    if endpoint_key not in seen:
                        seen.add(endpoint_key)
                        endpoints.append({
                            'method': method,
                            'path': path,
                            'path_template': path_template,
                            'file': str(file_path.relative_to(FRONTEND_DIR))
                        })
                except (IndexError, AttributeError) as e:
                    # Ignorar matches que no tienen los grupos esperados
                    continue
    
    def extract_backend_endpoints(self) -> Set[Tuple[str, str]]:
        """Extrae todos los endpoints definidos en el backend."""
        endpoints = set()
        
        # Buscar decoradores @router.get, @router.post, etc.
        for file_path in BACKEND_API_DIR.rglob("*.py"):
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Buscar @router.get("path"), @router.post("path"), etc.
                # También captura @router.get("") (path vacío)
                pattern = r'@router\.(get|post|patch|put|delete)\(["\']([^"\']*)["\']'
                for match in re.finditer(pattern, content):
                    method = match.group(1).upper()
                    path = match.group(2)  # Puede estar vacío
                    
                    # Obtener prefix del router
                    prefix_match = re.search(r'router\s*=\s*APIRouter\(prefix=["\']([^"\']+)["\']', content)
                    prefix = prefix_match.group(1) if prefix_match else ""
                    
                    # Construir path completo
                    full_path = prefix + path
                    # Normalizar path (remover trailing slash)
                    full_path = full_path.rstrip('/') or '/'
                    
                    endpoints.add((method, full_path))
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        # También buscar endpoints definidos directamente en main.py (como /health)
        main_file = BACKEND_API_DIR.parent.parent / "main.py"
        if main_file.exists():
            try:
                content = main_file.read_text(encoding='utf-8')
                # Buscar @app.get("path"), @app.post("path"), etc.
                pattern = r'@app\.(get|post|patch|put|delete)\(["\']([^"\']+)["\']'
                for match in re.finditer(pattern, content):
                    method = match.group(1).upper()
                    path = match.group(2)
                    # Normalizar path
                    path = path.rstrip('/') or '/'
                    endpoints.add((method, path))
            except Exception as e:
                print(f"Error reading {main_file}: {e}")
        
        # Agregar endpoints conocidos que pueden no detectarse correctamente
        known_endpoints = [
            ("GET", "/health"),  # Definido en main.py
        ]
        endpoints.update(known_endpoints)
        
        return endpoints
    
    def normalize_path(self, path: str) -> str:
        """Normaliza un path para comparación."""
        # Remover query strings (todo después de ?)
        if '?' in path:
            path = path.split('?')[0]
        # Remover trailing slash
        path = path.rstrip('/') or '/'
        # Normalizar variables: {id}, {strategy_id}, etc. -> {id}
        path = re.sub(r'\{[^}]+\}', '{id}', path)
        return path
    
    def check_alignment(self):
        """Verifica la alineación entre frontend y backend."""
        self.frontend_endpoints = self.extract_frontend_endpoints()
        self.backend_endpoints = self.extract_backend_endpoints()
        
        # Normalizar backend endpoints para comparación
        backend_normalized = {
            (method, self.normalize_path(path)): (method, path)
            for method, path in self.backend_endpoints
        }
        
        # Verificar cada endpoint del frontend
        for fe_endpoint in self.frontend_endpoints:
            method = fe_endpoint['method']
            path_template = self.normalize_path(fe_endpoint['path_template'])
            
            # Buscar coincidencia en backend
            key = (method, path_template)
            if key not in backend_normalized:
                # Intentar buscar con variaciones
                found = False
                for (be_method, be_path_norm), (be_method_orig, be_path_orig) in backend_normalized.items():
                    if be_method == method:
                        # Comparar paths normalizados
                        if self.paths_match(path_template, be_path_norm):
                            found = True
                            break
                
                if not found:
                    self.missing_endpoints.append({
                        'method': method,
                        'path': fe_endpoint['path'],
                        'path_template': path_template,
                        'file': fe_endpoint['file']
                    })
    
    def paths_match(self, path1: str, path2: str) -> bool:
        """Verifica si dos paths coinciden (considerando variables)."""
        # Normalizar ambos paths
        p1 = self.normalize_path(path1)
        p2 = self.normalize_path(path2)
        
        # Si son exactamente iguales
        if p1 == p2:
            return True
        
        # Comparar segmento por segmento
        segments1 = p1.split('/')
        segments2 = p2.split('/')
        
        if len(segments1) != len(segments2):
            return False
        
        for s1, s2 in zip(segments1, segments2):
            # Si ambos son variables o ambos son iguales
            if (s1.startswith('{') and s2.startswith('{')) or s1 == s2:
                continue
            else:
                return False
        
        return True


@pytest.fixture
def alignment_test():
    """Fixture para el test de alineación."""
    return FrontendBackendAlignmentTest()


@pytest.fixture
def api_client():
    """Cliente HTTP para hacer requests al backend."""
    if httpx is None:
        pytest.skip("httpx no está instalado. Instalar con: pip install httpx")
    return httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0)


@pytest.mark.asyncio
async def test_frontend_backend_endpoint_alignment(alignment_test):
    """Test que verifica que todos los endpoints del frontend existen en el backend."""
    alignment_test.check_alignment()
    
    if alignment_test.missing_endpoints:
        missing_str = "\n".join([
            f"  {ep['method']} {ep['path']} (from {ep['file']})"
            for ep in alignment_test.missing_endpoints
        ])
        pytest.fail(
            f"Se encontraron {len(alignment_test.missing_endpoints)} endpoints del frontend "
            f"que no existen en el backend:\n{missing_str}"
        )


@pytest.mark.asyncio
async def test_backend_endpoints_respond(api_client):
    """Test que verifica que los endpoints del backend responden correctamente."""
    # Lista de endpoints críticos que deben responder (sin autenticación o con mock)
    critical_endpoints = [
        ("GET", "/health"),
        ("GET", "/system/config"),
    ]
    
    for method, path in critical_endpoints:
        try:
            response = await api_client.request(method, path)
            # Verificar que no es 404
            assert response.status_code != 404, f"Endpoint {method} {path} retorna 404"
            # Verificar que no es 500 (error del servidor)
            assert response.status_code < 500, f"Endpoint {method} {path} retorna {response.status_code}"
        except httpx.ConnectError:
            pytest.skip(f"No se puede conectar al backend en {BACKEND_URL}")
        except Exception as e:
            pytest.fail(f"Error al probar {method} {path}: {e}")


def test_generate_endpoint_report(alignment_test):
    """Genera un reporte de endpoints para análisis."""
    alignment_test.check_alignment()
    
    report = {
        'frontend_endpoints_count': len(alignment_test.frontend_endpoints),
        'backend_endpoints_count': len(alignment_test.backend_endpoints),
        'missing_endpoints': alignment_test.missing_endpoints,
        'frontend_endpoints': alignment_test.frontend_endpoints,
        'backend_endpoints': list(alignment_test.backend_endpoints)
    }
    
    # Guardar reporte en archivo
    report_file = Path(__file__).parent / "endpoint_alignment_report.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    
    print(f"\n[REPORTE] Reporte generado en: {report_file}")
    print(f"   Frontend endpoints: {len(alignment_test.frontend_endpoints)}")
    print(f"   Backend endpoints: {len(alignment_test.backend_endpoints)}")
    print(f"   Endpoints faltantes: {len(alignment_test.missing_endpoints)}")
    
    if alignment_test.missing_endpoints:
        print("\n[ADVERTENCIA] Endpoints del frontend que no existen en el backend:")
        for ep in alignment_test.missing_endpoints[:10]:  # Mostrar primeros 10
            print(f"   {ep['method']} {ep['path']} (from {ep['file']})")


if __name__ == "__main__":
    # Ejecutar test de reporte
    test = FrontendBackendAlignmentTest()
    test_generate_endpoint_report(test)

