"""Configuração central da API (12-factor: tudo via ambiente)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="NEFRON_", extra="ignore")

    # Aplicação
    app_name: str = "Néfron API"
    environment: str = "development"
    debug: bool = False

    # Banco (Supabase Postgres — apenas como banco; auth é próprio da API)
    database_url: str = "postgresql+asyncpg://nefron:nefron@localhost:5432/nefron"

    # JWT (HS256 por padrão; pronto para RS256/ICP-Brasil em produção)
    jwt_secret: str = "troque-em-producao-use-segredo-forte"
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 30
    refresh_token_ttl_days: int = 7
    mfa_token_ttl_min: int = 5  # token intermediário entre senha e 2FA

    # 2FA
    totp_issuer: str = "Nefron"

    # VIDaaS (certificado em nuvem ICP-Brasil — Valid / CRM Digital)
    # Padrão PSC ICP-Brasil: OAuth2 authorization_code + PKCE, escopo de sessão
    # de assinatura. Sem client_id configurado (ou com vidaas_mock=true), o
    # sistema usa o provedor SIMULADO — útil em dev/teste e homologação.
    vidaas_base_url: str = "https://certificado.vidaas.com.br"
    vidaas_client_id: str = ""
    vidaas_client_secret: str = ""
    vidaas_redirect_uri: str = "http://localhost:8000/api/v1/assinatura/vidaas/callback"
    vidaas_mock: bool = False
    vidaas_token_ttl_min: int = 30  # janela p/ usar a sessão de assinatura

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
