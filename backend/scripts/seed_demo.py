"""Cria dados de demonstração: unidade, médico (com senha), vínculo e paciente.

Uso:
    python -m scripts.seed_demo

Credenciais criadas:
    e-mail: ana@nefron.com.br   senha: Nefron@2026
O 2FA é configurado no primeiro login (POST /auth/2fa/enroll).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import uuid

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.clinico import Evolucao, ExameResultado, RefExame
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

        # Um login demo por segmento (mesma senha) — enfermeiro, técnico e
        # equipe multiprofissional
        outros = [
            ("Enf. Carlos Lima", "carlos@nefron.com.br", "COREN", "enfermeiro"),
            ("Téc. Tânia Souza", "tania@nefron.com.br", "COREN", "tecnico"),
            ("Nut. Júlia Prado", "julia@nefron.com.br", "CRN", "equipe_multi"),
        ]
        for nome, email, conselho, papel in outros:
            prof = Profissional(nome=nome, email=email, conselho_tipo=conselho,
                                senha_hash=hash_password(DEMO_SENHA),
                                totp_ativo=False)
            s.add(prof)
            await s.flush()
            s.add(Vinculo(profissional_id=prof.id, unidade_id=unidade.id,
                          papel=papel))

        paciente = Paciente(
            id=uuid.uuid4(), nome="Maria Silva", cns="700000000000001",
            sexo="feminino", data_nascimento=dt.date(1967, 3, 12),
            etiologia_drc="Nefropatia diabética", estagio_drc=5,
            segmento="hemodialise",
            inicio_trs=dt.date(2022, 6, 1), turno_dialise="manha",
        )
        s.add(paciente)
        await s.flush()
        s.add(PacienteUnidade(paciente_id=paciente.id, unidade_id=unidade.id))

        # Paciente do ambulatório conservador (estágio 4 — candidato a preparo TRS)
        conservador = Paciente(
            id=uuid.uuid4(), nome="João Pereira", cns="700000000000002",
            sexo="masculino", data_nascimento=dt.date(1955, 9, 2),
            etiologia_drc="Hipertensão arterial", estagio_drc=4,
            segmento="conservador",
        )
        s.add(conservador)
        await s.flush()
        s.add(PacienteUnidade(paciente_id=conservador.id, unidade_id=unidade.id))

        # Série de Hemoglobina (mostra tendência de queda / fora da meta) — o seed.sql
        # deve ter sido aplicado (ref.exame com código 'HB').
        hb = await s.scalar(select(RefExame).where(RefExame.codigo == "HB"))
        if hb is not None:
            base = dt.datetime(2026, 4, 1, tzinfo=dt.timezone.utc)
            for i, valor in enumerate([11.2, 10.6, 9.9, 9.4]):
                s.add(ExameResultado(
                    paciente_id=paciente.id, exame_id=hb.id, valor=valor,
                    unidade="g/dL", data_coleta=base + dt.timedelta(days=30 * i),
                    fora_faixa=valor < 10,
                ))

        s.add(Evolucao(
            paciente_id=paciente.id, profissional_id=medico.id, categoria="medica",
            subjetivo="Refere melhora da disposição.",
            avaliacao="DRC estágio 5 em HD, anemia com Hb em queda.",
            plano="Otimizar eritropoetina; solicitar ferritina/TSAT.",
            assinada_em=dt.datetime.now(dt.timezone.utc),
        ))

        await s.commit()
        print(f"OK — login: {DEMO_EMAIL} / {DEMO_SENHA} (configure o 2FA no 1º acesso)")


if __name__ == "__main__":
    asyncio.run(main())
