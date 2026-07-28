# Néfron — API (FastAPI)

Backend do Prontuário Eletrônico Nefrológico. **Auth próprio** (JWT + 2FA TOTP);
Supabase usado apenas como PostgreSQL. RLS dirigido por GUC de sessão.

## Estrutura

```
backend/
├── pyproject.toml
├── .env.example
└── app/
    ├── main.py                 # FastAPI app + CORS + /health
    ├── core/
    │   ├── config.py           # settings (env NEFRON_*)
    │   ├── security.py         # Argon2 + JWT + TOTP (pyotp)
    │   ├── database.py         # engine async + set_rls_context (GUC)
    │   └── deps.py             # get_current_user, require_roles, sessão RLS
    ├── models/core.py          # ORM: Unidade, Profissional, Vinculo, Paciente
    ├── schemas/                # DTOs Pydantic (auth, dashboard)
    ├── services/               # regras (auth_service, dashboard_service)
    └── api/                    # rotas (auth, dashboard) + router v1
```

## Fluxo de autenticação (2 passos + contexto)

```
1. POST /api/v1/auth/login        {email, senha}      → {mfa_token, totp_enrollment_required}
   (primeiro acesso) POST /api/v1/auth/2fa/enroll?mfa_token=…  → {secret, otpauth_uri (QR)}
2. POST /api/v1/auth/2fa/verify   {mfa_token, codigo} → {refresh_token, vinculos[]}
3. POST /api/v1/auth/context      {refresh_token, unidade_id, papel} → {access_token, ...}

Depois: Authorization: Bearer <access_token>
        GET /api/v1/dashboard  → dashboard do perfil ativo
```

O access token carrega o **contexto ativo** (unidade + papel). O RBAC é aplicado em
`require_roles(...)` e a sessão de banco define `app.profissional_id`/`app.ator_id`
para RLS + auditoria (hash-chain).

## Como rodar (local)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Banco: aplique o schema e as adaptações do auth próprio
psql "$DB" -f ../db/schema.sql
psql "$DB" -f ../db/auth_fastapi_columns.sql
psql "$DB" -f ../db/rls_fastapi_context.sql
psql "$DB" -f ../db/seed.sql
psql "$DB" -f ../db/interacoes.sql
psql "$DB" -f ../db/escala.sql
python -m scripts.seed_demo          # usuário demo

cp .env.example .env                 # ajuste NEFRON_DATABASE_URL/JWT_SECRET
uvicorn app.main:app --reload        # http://localhost:8000/docs
```

## Testes

```bash
pytest                 # test_security (sem DB) sempre roda
NEFRON_TEST_DATABASE_URL=postgresql+asyncpg://... pytest   # inclui integração
```

## Segurança

- Senhas com **Argon2** (rehash automático). Mensagens de login genéricas (anti-enumeração).
- **2FA TOTP obrigatório** (pyotp), com QR via `otpauth://`.
- Tokens tipados (`mfa`/`access`/`refresh`); access curto com contexto ativo.
- RLS como última linha de defesa (GUC por transação).
