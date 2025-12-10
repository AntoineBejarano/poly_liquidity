"""
Authentication middleware for Stack OAuth.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from app.settings import settings
from app.database import SessionLocal
from app.models.user import UserMetadata
from app.models.user_sync import UserSync

security = HTTPBearer()


class User:
    """
    Combined user object that merges data from neon_auth.users_sync and user_metadata.
    This is a convenience class for the API layer.
    """
    def __init__(self, user_sync: UserSync, metadata: Optional[UserMetadata] = None):
        self.id = user_sync.id
        self.email = user_sync.email
        self.name = user_sync.name
        self.created_at = user_sync.created_at
        self.updated_at = user_sync.updated_at
        self.role = metadata.role if metadata else "viewer"
        self._user_sync = user_sync
        self._metadata = metadata


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Validate JWT token from Stack OAuth and return current user.
    
    The user data comes from neon_auth.users_sync (managed by Stack Auth).
    Additional metadata (like role) comes from user_metadata.
    """
    token = credentials.credentials
    
    try:
        # Verify token with Stack OAuth
        # In production, fetch JWKS from Stack OAuth
        # For now, we'll decode and validate the token
        # TODO: Implement proper JWKS validation
        
        # Decode token (without verification for now - needs JWKS)
        try:
            decoded = jwt.decode(
                token,
                options={"verify_signature": False}  # TODO: Remove this and verify properly
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Extract user info
        user_id = decoded.get("sub")  # This is the user ID from Stack Auth
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            )
        
        # Get user from neon_auth.users_sync (managed by Stack Auth)
        db = SessionLocal()
        try:
            # Query neon_auth.users_sync
            user_sync = db.query(UserSync).filter(
                UserSync.id == user_id,
                UserSync.deleted_at.is_(None)  # Only active users
            ).first()
            
            if not user_sync:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found in system"
                )
            
            # Get or create metadata
            metadata = db.query(UserMetadata).filter(
                UserMetadata.user_id == user_id
            ).first()
            
            if not metadata:
                # Create default metadata
                metadata = UserMetadata(
                    user_id=user_id,
                    role="viewer",  # Default role
                )
                db.add(metadata)
                db.commit()
                db.refresh(metadata)
            
            return User(user_sync, metadata)
        finally:
            db.close()
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

