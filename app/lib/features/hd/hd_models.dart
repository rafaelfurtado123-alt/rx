/// Modelos de prescrição de HD e sessão (espelham os DTOs do FastAPI).

class AlertaItem {
  final String tipo;
  final String gravidade; // 'bloqueio' | 'alerta' | 'info'
  final String mensagem;
  const AlertaItem(
      {required this.tipo, required this.gravidade, required this.mensagem});

  factory AlertaItem.fromJson(Map<String, dynamic> j) => AlertaItem(
        tipo: j['tipo'] as String,
        gravidade: j['gravidade'] as String,
        mensagem: j['mensagem'] as String,
      );
}

class AcessoVascular {
  final String id;
  final String tipo;
  final String? lado;
  final String? localizacao;
  final String status;
  const AcessoVascular(
      {required this.id,
      required this.tipo,
      this.lado,
      this.localizacao,
      required this.status});

  factory AcessoVascular.fromJson(Map<String, dynamic> j) => AcessoVascular(
        id: j['id'] as String,
        tipo: j['tipo'] as String,
        lado: j['lado'] as String?,
        localizacao: j['localizacao'] as String?,
        status: j['status'] as String,
      );

  String get rotulo {
    const nomes = {
      'fav': 'FAV',
      'protese': 'Prótese',
      'cateter_tunelizado': 'Cateter tunelizado',
      'cateter_temporario': 'Cateter temporário',
      'peritoneal': 'Peritoneal',
    };
    final partes = [nomes[tipo] ?? tipo, if (lado != null) lado!, if (localizacao != null) localizacao!];
    return partes.join(' · ');
  }
}

class PrescricaoHD {
  final String id;
  final String modalidade;
  final int duracaoMin;
  final int? qbMlMin, qdMlMin;
  final String? dialisadorModelo;
  final String? acessoId;
  final double? pesoAtualKg, pesoSecoKg, ufPrescritaL, ufMaximaL, volumeCalculadoL;
  final String status;
  final DateTime? assinadaEm;
  final List<AlertaItem> alertas;
  const PrescricaoHD({
    required this.id,
    required this.modalidade,
    required this.duracaoMin,
    this.qbMlMin,
    this.qdMlMin,
    this.dialisadorModelo,
    this.acessoId,
    this.pesoAtualKg,
    this.pesoSecoKg,
    this.ufPrescritaL,
    this.ufMaximaL,
    this.volumeCalculadoL,
    required this.status,
    this.assinadaEm,
    this.alertas = const [],
  });

  factory PrescricaoHD.fromJson(Map<String, dynamic> j) => PrescricaoHD(
        id: j['id'] as String,
        modalidade: j['modalidade'] as String,
        duracaoMin: j['duracao_min'] as int,
        qbMlMin: j['qb_ml_min'] as int?,
        qdMlMin: j['qd_ml_min'] as int?,
        dialisadorModelo: j['dialisador_modelo'] as String?,
        acessoId: j['acesso_id'] as String?,
        pesoAtualKg: (j['peso_atual_kg'] as num?)?.toDouble(),
        pesoSecoKg: (j['peso_seco_kg'] as num?)?.toDouble(),
        ufPrescritaL: (j['uf_prescrita_l'] as num?)?.toDouble(),
        ufMaximaL: (j['uf_maxima_l'] as num?)?.toDouble(),
        volumeCalculadoL: (j['volume_calculado_l'] as num?)?.toDouble(),
        status: j['status'] as String,
        assinadaEm: j['assinada_em'] == null
            ? null
            : DateTime.parse(j['assinada_em'] as String),
        alertas: ((j['alertas'] as List?) ?? const [])
            .map((e) => AlertaItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class SessaoHD {
  final String id;
  final String? prescricaoHdId;
  final double? pesoPreKg, tempPre, pesoPosKg, ufRealL, ktv, urr, npcr;
  final String? paPre, paPos, queixas, maquina;
  final int? fcPre, fcPos;
  final DateTime? inicio, fim;
  final List<AlertaItem> alertas;
  const SessaoHD({
    required this.id,
    this.prescricaoHdId,
    this.pesoPreKg,
    this.paPre,
    this.fcPre,
    this.tempPre,
    this.queixas,
    this.inicio,
    this.fim,
    this.maquina,
    this.pesoPosKg,
    this.ufRealL,
    this.paPos,
    this.fcPos,
    this.ktv,
    this.urr,
    this.npcr,
    this.alertas = const [],
  });

  bool get emAndamento => inicio != null && fim == null;
  bool get encerrada => fim != null;

  factory SessaoHD.fromJson(Map<String, dynamic> j) => SessaoHD(
        id: j['id'] as String,
        prescricaoHdId: j['prescricao_hd_id'] as String?,
        pesoPreKg: (j['peso_pre_kg'] as num?)?.toDouble(),
        paPre: j['pa_pre'] as String?,
        fcPre: j['fc_pre'] as int?,
        tempPre: (j['temp_pre'] as num?)?.toDouble(),
        queixas: j['queixas'] as String?,
        inicio:
            j['inicio'] == null ? null : DateTime.parse(j['inicio'] as String),
        fim: j['fim'] == null ? null : DateTime.parse(j['fim'] as String),
        maquina: j['maquina'] as String?,
        pesoPosKg: (j['peso_pos_kg'] as num?)?.toDouble(),
        ufRealL: (j['uf_real_l'] as num?)?.toDouble(),
        paPos: j['pa_pos'] as String?,
        fcPos: j['fc_pos'] as int?,
        ktv: (j['ktv'] as num?)?.toDouble(),
        urr: (j['urr'] as num?)?.toDouble(),
        npcr: (j['npcr'] as num?)?.toDouble(),
        alertas: ((j['alertas'] as List?) ?? const [])
            .map((e) => AlertaItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
