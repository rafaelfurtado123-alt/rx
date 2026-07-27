"""Testes unitários das primitivas de segurança (sem banco)."""
from __future__ import annotations

import datetime as dt

import jwt
import pyotp
import pytest

from app.core import security


def test_password_hash_and_verify():
    h = security.hash_password("Nefron@2026")
    assert h != "Nefron@2026"
    assert security.verify_password("Nefron@2026", h)
    assert not security.verify_password("senha-errada", h)


def test_totp_roundtrip():
    secret = security.generate_totp_secret()
    code = pyotp.TOTP(secret).now()
    assert security.verify_totp(secret, code)
    assert not security.verify_totp(secret, "000000")


def test_access_token_carries_context():
    token = security.create_access_token("prof-1", "uni-1", "medico")
    payload = security.decode_token(token, "access")
    assert payload["sub"] == "prof-1"
    assert payload["unidade_id"] == "uni-1"
    assert payload["papel"] == "medico"


def test_token_type_is_enforced():
    mfa = security.create_mfa_token("prof-1")
    # Decodificar um token 'mfa' como 'access' deve falhar
    with pytest.raises(jwt.InvalidTokenError):
        security.decode_token(mfa, "access")


def test_expired_token_rejected():
    token = security.create_token("p", "access", dt.timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_token(token, "access")
