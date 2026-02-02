#!/usr/bin/env python3
"""
Arranque del servidor backend sin --reload.

En Windows, uvicorn --reload puede provocar PermissionError [WinError 5]
(Acceso denegado) por el uso de Named Pipes en multiprocessing.
Este script arranca uvicorn sin recarga automática para evitar ese error.

Uso:
  cd backend
  python run_server.py

O con host/puerto:
  python run_server.py --host 0.0.0.0 --port 8000
"""
import sys
import uvicorn


def main() -> None:
    host = "0.0.0.0"
    port = 8000
    if "--host" in sys.argv:
        i = sys.argv.index("--host")
        if i + 1 < len(sys.argv):
            host = sys.argv[i + 1]
    if "--port" in sys.argv:
        i = sys.argv.index("--port")
        if i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    # Sin --reload para evitar WinError 5 en Windows (CreateNamedPipe)
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
