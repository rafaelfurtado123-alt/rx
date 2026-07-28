"""Agregador de rotas da API v1."""
from __future__ import annotations

from fastapi import APIRouter

from . import routes_auth, routes_dashboard, routes_hd, routes_prontuario

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(routes_auth.router)
api_router.include_router(routes_dashboard.router)
api_router.include_router(routes_prontuario.router)
api_router.include_router(routes_hd.router)
