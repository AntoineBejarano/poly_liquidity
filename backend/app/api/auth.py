"""
Authentication middleware for Stack OAuth.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
import json
import os
from datetime import datetime
from app.settings import settings
from app.database import SessionLocal
from app.models.user import UserMetadata
from app.models.user_sync import UserSync

security = HTTPBearer(auto_error=False)

# #region agent log
LOG_PATH = r"c:\develop\repositorios\poly_liquidity\.cursor\debug.log"
def _log_debug(session_id: str, run_id: str, hypothesis_id: str, location: str, message: str, data: dict):
    try:
        log_entry = {
            "sessionId": session_id,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(datetime.now().timestamp() * 1000)
        }
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
# #endregion


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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """
    Validate JWT token from Stack OAuth and return current user.
    
    The user data comes from neon_auth.users_sync (managed by Stack Auth).
    Additional metadata (like role) comes from user_metadata.
    """
    # #region agent log
    _log_debug("debug-session", "run1", "D", "auth.py:64", "get_current_user entry", {"has_credentials": credentials is not None, "credentials_type": type(credentials).__name__ if credentials else None})
    # #endregion
    
    if not credentials:
        # #region agent log
        _log_debug("debug-session", "run1", "D", "auth.py:70", "No credentials provided", {})
        # #endregion
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    
    token = credentials.credentials
    
    # #region agent log
    _log_debug("debug-session", "run1", "D", "auth.py:75", "Token extracted", {"has_token": token is not None, "token_preview": token[:20] + "..." if token and len(token) > 20 else token if token else None, "token_length": len(token) if token else 0})
    # #endregion
    
    try:
        # Verify token with Stack OAuth
        # In production, fetch JWKS from Stack OAuth
        # For now, we'll decode and validate the token
        # TODO: Implement proper JWKS validation
        
        # Decode token (without verification for now - needs JWKS)
        try:
            # jose.jwt.decode requires a key parameter even when verify_signature=False
            # We pass an empty string as key when not verifying
            decoded = jwt.decode(
                token,
                key="",  # Empty key since we're not verifying signature
                options={
                    "verify_signature": False,  # TODO: Remove this and verify properly
                    "verify_aud": False,  # Don't verify audience
                    "verify_exp": False,  # Don't verify expiration (for now)
                }
            )
            # #region agent log
            _log_debug("debug-session", "run1", "G", "auth.py:82", "Token decoded successfully", {"has_sub": "sub" in decoded, "token_keys": list(decoded.keys())})
            # #endregion
        except JWTError as e:
            # #region agent log
            _log_debug("debug-session", "run1", "G", "auth.py:87", "JWT decode error", {"error_type": type(e).__name__, "error_msg": str(e)})
            # #endregion
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Extract user info
        user_id = decoded.get("sub")  # This is the user ID from Stack Auth
        
        # #region agent log
        _log_debug("debug-session", "run1", "A", "auth.py:98", "User ID extracted from token", {"user_id": user_id, "user_id_type": type(user_id).__name__, "user_id_length": len(str(user_id)) if user_id else 0})
        # #endregion
        
        if not user_id:
            # #region agent log
            _log_debug("debug-session", "run1", "A", "auth.py:103", "No user_id in token", {"decoded_keys": list(decoded.keys())})
            # #endregion
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            )
        
        # Get user from neon_auth.users_sync (managed by Stack Auth)
        db = SessionLocal()
        try:
            # #region agent log
            _log_debug("debug-session", "run1", "C", "auth.py:114", "Starting DB query for user", {"user_id": user_id})
            # #endregion
            
            # Query neon_auth.users_sync
            user_sync = db.query(UserSync).filter(
                UserSync.id == user_id,
                UserSync.deleted_at.is_(None)  # Only active users
            ).first()
            
            # #region agent log
            _log_debug("debug-session", "run1", "A", "auth.py:124", "User query result", {"user_found": user_sync is not None, "user_id_queried": user_id})
            # #endregion
            
            if not user_sync:
                # #region agent log
                # Check if user exists but is deleted
                user_deleted = db.query(UserSync).filter(UserSync.id == user_id).first()
                _log_debug("debug-session", "run1", "B", "auth.py:131", "User not found - checking if deleted", {"user_exists": user_deleted is not None, "deleted_at": str(user_deleted.deleted_at) if user_deleted else None, "user_id": user_id})
                # Check all users to see if there's a format mismatch
                all_user_ids = db.query(UserSync.id).limit(5).all()
                _log_debug("debug-session", "run1", "F", "auth.py:134", "Sample user IDs in DB", {"sample_ids": [str(uid[0]) for uid in all_user_ids], "queried_id": user_id, "queried_id_type": type(user_id).__name__})
                # #endregion
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found in system"
                )
            
            # #region agent log
            _log_debug("debug-session", "run1", "A", "auth.py:142", "User found in users_sync", {"user_id": user_sync.id, "email": user_sync.email, "deleted_at": str(user_sync.deleted_at)})
            # #endregion
            
            # Get or create metadata
            metadata = db.query(UserMetadata).filter(
                UserMetadata.user_id == user_id
            ).first()
            
            # #region agent log
            _log_debug("debug-session", "run1", "A", "auth.py:151", "Metadata query result", {"metadata_found": metadata is not None, "user_id": user_id})
            # #endregion
            
            if not metadata:
                # Create default metadata
                metadata = UserMetadata(
                    user_id=user_id,
                    role="viewer",  # Default role
                )
                db.add(metadata)
                db.commit()
                db.refresh(metadata)
                # #region agent log
                _log_debug("debug-session", "run1", "A", "auth.py:164", "Metadata created", {"user_id": user_id, "role": metadata.role})
                # #endregion
            
            # #region agent log
            _log_debug("debug-session", "run1", "A", "auth.py:168", "Authentication successful", {"user_id": user_sync.id, "email": user_sync.email, "role": metadata.role})
            # #endregion
            return User(user_sync, metadata)
        except HTTPException:
            raise
        except Exception as e:
            # #region agent log
            _log_debug("debug-session", "run1", "C", "auth.py:175", "Database error", {"error_type": type(e).__name__, "error_msg": str(e), "user_id": user_id})
            # #endregion
            raise
        finally:
            db.close()
    
    except HTTPException:
        raise
    except JWTError as e:
        # #region agent log
        _log_debug("debug-session", "run1", "G", "auth.py:185", "JWTError in outer catch", {"error_type": type(e).__name__, "error_msg": str(e)})
        # #endregion
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        # #region agent log
        _log_debug("debug-session", "run1", "E", "auth.py:193", "Unexpected exception", {"error_type": type(e).__name__, "error_msg": str(e)})
        # #endregion
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

