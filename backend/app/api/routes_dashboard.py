"""Rotas de dashboard (por perfil)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import get_authed_session, get_current_user
from ..schemas.auth import CurrentUser
from ..schemas.dashboard import DashboardResponse
from ..services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authed_session),
):
    """Dashboard do perfil ativo (métricas + alertas), isolado por unidade via RLS."""
    return await dashboard_service.build_dashboard(session, user)
