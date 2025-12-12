"""
Runtime Supervisor API endpoints.
"""
from fastapi import APIRouter, Depends
from app.core.runtime_supervisor import RuntimeSupervisor
from app.main import runtime_supervisor
from app.api.auth import get_current_user
from app.api.auth import User

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/status")
async def get_runtime_status(
    current_user: User = Depends(get_current_user),
):
    """
    Get current runtime supervisor status.
    
    Returns:
        - mode: Current runtime mode (GREEN/YELLOW/RED)
        - circuit_breakers: State of all circuit breakers
        - fail_safes: State of fail-safes
        - metrics: Current metrics snapshot
    """
    return runtime_supervisor.get_status()


@router.get("/mode")
async def get_runtime_mode(
    current_user: User = Depends(get_current_user),
):
    """
    Get current runtime mode.
    
    Returns:
        - mode: Current runtime mode (GREEN/YELLOW/RED)
    """
    return {
        "mode": runtime_supervisor.get_mode().value
    }


@router.get("/circuit-breakers")
async def get_circuit_breakers(
    current_user: User = Depends(get_current_user),
):
    """
    Get state of all circuit breakers.
    
    Returns:
        - circuit_breakers: Dict with state of each circuit breaker
    """
    status = runtime_supervisor.get_status()
    return {
        "circuit_breakers": status["circuit_breakers"]
    }


@router.get("/fail-safes")
async def get_fail_safes(
    current_user: User = Depends(get_current_user),
):
    """
    Get state of all fail-safes.
    
    Returns:
        - fail_safes: Dict with state of each fail-safe
    """
    status = runtime_supervisor.get_status()
    return {
        "fail_safes": status["fail_safes"]
    }

