"""Primitivas de segurança: hash de senha (Argon2), JWT e 2FA (TOTP).

Auth é próprio da API (não usa Supabase Auth). Tokens:
  * ``mfa``     — intermediário, emitido após a senha; só serve para verificar o 2FA.
  * ``access``  — token de acesso curto, com contexto ativo (unidade + papel).
  * ``refresh`` — token de renovação.
"""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Literal

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .config import get_settings

_ph = PasswordHasher()
TokenType = Literal["mfa", "access", "refresh"]


# ----------------------------- Senha (Argon2) -----------------------------
def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


# ----------------------------- JWT -----------------------------
def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def create_token(
    subject: str,
    token_type: TokenType,
    ttl: dt.timedelta,
    extra: dict[str, Any] | None = None,
) -> str:
    s = get_settings()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": _now(),
        "exp": _now() + ttl,
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    s = get_settings()
    payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"tipo de token inválido: esperado {expected_type}")
    return payload


def create_mfa_token(profissional_id: str) -> str:
    s = get_settings()
    return create_token(profissional_id, "mfa", dt.timedelta(minutes=s.mfa_token_ttl_min))


def create_access_token(
    profissional_id: str,
    unidade_id: str | None,
    papel: str | None,
    nome: str | None = None,
) -> str:
    """Access token com o CONTEXTO ATIVO (unidade + papel) escolhido no login."""
    s = get_settings()
    return create_token(
        profissional_id,
        "access",
        dt.timedelta(minutes=s.access_token_ttl_min),
        extra={"unidade_id": unidade_id, "papel": papel, "nome": nome},
    )


def create_refresh_token(profissional_id: str) -> str:
    s = get_settings()
    return create_token(
        profissional_id, "refresh", dt.timedelta(days=s.refresh_token_ttl_days)
    )


# ----------------------------- 2FA (TOTP) -----------------------------
def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, account_name: str) -> str:
    """URI otpauth:// para gerar QR code em apps como Google Authenticator/Authy."""
    s = get_settings()
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=s.totp_issuer)


def verify_totp(secret: str, code: str) -> bool:
    # valid_window=1 tolera pequeno desvio de relógio (±30s).
    return pyotp.TOTP(secret).verify(code, valid_window=1)
