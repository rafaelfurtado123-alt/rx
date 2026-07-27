"""Cria dados de demonstração: unidade, médico (com senha), vínculo e paciente.

Uso:
    python -m scripts.seed_demo

Credenciais criadas:
    e-mail: ana@nefron.com.br   senha: Nefron@2026
O 2FA é configurado no primeiro login (POST /auth/2fa/enroll).
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.core import Paciente, PacienteUnidade, Profissional, Unidade, Vinculo

DEMO_EMAIL = "ana@nefron.com.br"
DEMO_SENHA = "Nefron@2026"


async def main() -> None:
    async with SessionLocal() as s:
        existing = await s.scalar(
            select(Profissional).where(Profissional.email == DEMO_EMAIL)
        )
        if existing:
            print("Demo já existe — nada a fazer.")
            return

        unidade = Unidade(id=uuid.uuid4(), nome="Clínica Néfron", cnes="1234567",
                          tipo="clinica_dialise")
        medico = Profissional(
            id=uuid.uuid4(),
            nome="Dra. Ana Nefro",
            email=DEMO_EMAIL,
            conselho_tipo="CRM",
            conselho_num="123456",
            conselho_uf="SP",
            especialidade="Nefrologia",
            senha_hash=hash_password(DEMO_SENHA),
            totp_ativo=False,
        )
        s.add_all([unidade, medico])
        await s.flush()

        s.add(Vinculo(profissional_id=medico.id, unidade_id=unidade.id, papel="medico"))

        paciente = Paciente(id=uuid.uuid4(), nome="Maria Silva",
                            cns="700000000000001", estagio_drc=5, turno_dialise="manha")
        s.add(paciente)
        await s.flush()
        s.add(PacienteUnidade(paciente_id=paciente.id, unidade_id=unidade.id))

        await s.commit()
        print(f"OK — login: {DEMO_EMAIL} / {DEMO_SENHA} (configure o 2FA no 1º acesso)")


if __name__ == "__main__":
    asyncio.run(main())
