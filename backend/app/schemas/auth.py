"""DTOs de autenticação."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=6)


class LoginResponse(BaseModel):
    """Passo 1: senha validada. Exige verificação de 2FA para prosseguir."""
    mfa_required: bool = True
    mfa_token: str
    totp_enrollment_required: bool = False  # true no primeiro acesso (sem 2FA ainda)


class TotpEnrollResponse(BaseModel):
    secret: str
    otpauth_uri: str  # gerar QR code no cliente


class Verify2FARequest(BaseModel):
    mfa_token: str
    codigo: str = Field(min_length=6, max_length=6)


class VinculoOut(BaseModel):
    unidade_id: uuid.UUID
    unidade_nome: str
    papel: str


class Verify2FAResponse(BaseModel):
    """Passo 2: 2FA ok. Retorna refresh + lista de vínculos para escolher contexto."""
    refresh_token: str
    vinculos: list[VinculoOut]


class SelectContextRequest(BaseModel):
    refresh_token: str
    unidade_id: uuid.UUID
    papel: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    unidade_id: uuid.UUID
    papel: str


class CurrentUser(BaseModel):
    profissional_id: uuid.UUID
    nome: str
    unidade_id: uuid.UUID | None
    papel: str | None
