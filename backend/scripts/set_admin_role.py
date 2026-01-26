"""
Script para establecer el rol de admin a un usuario.

Uso:
    python scripts/set_admin_role.py <email>
    
Ejemplo:
    python scripts/set_admin_role.py admin@example.com
"""
import sys
import os
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import UserMetadata
from app.models.user_sync import UserSync

def set_admin_role(email: str):
    """Establece el rol de admin para un usuario por email."""
    db = SessionLocal()
    try:
        # Buscar usuario por email en neon_auth.users_sync
        user_sync = db.query(UserSync).filter(
            UserSync.email == email,
            UserSync.deleted_at.is_(None)
        ).first()
        
        if not user_sync:
            print(f"[ERROR] Usuario con email '{email}' no encontrado")
            print("\nUsuarios disponibles:")
            users = db.query(UserSync).filter(UserSync.deleted_at.is_(None)).all()
            for u in users:
                print(f"  - {u.email} (ID: {u.id})")
            return False
        
        print(f"[OK] Usuario encontrado: {user_sync.email} (ID: {user_sync.id})")
        
        # Buscar o crear metadata
        metadata = db.query(UserMetadata).filter(
            UserMetadata.user_id == user_sync.id
        ).first()
        
        if not metadata:
            print("  Creando metadata...")
            metadata = UserMetadata(
                user_id=user_sync.id,
                role="admin"
            )
            db.add(metadata)
        else:
            print(f"  Rol actual: {metadata.role}")
            metadata.role = "admin"
        
        db.commit()
        print(f"[OK] Rol actualizado a 'admin' para {user_sync.email}")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/set_admin_role.py <email>")
        print("\nEjemplo:")
        print("  python scripts/set_admin_role.py admin@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    success = set_admin_role(email)
    sys.exit(0 if success else 1)

