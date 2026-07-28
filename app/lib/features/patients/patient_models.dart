/// Modelos do prontuário (espelham os DTOs do FastAPI).

class PacienteResumo {
  final String id;
  final String nome;
  final String? cns;
  final int? estagioDrc;
  final String? segmento;
  final String? turnoDialise;
  const PacienteResumo(
      {required this.id,
      required this.nome,
      this.cns,
      this.estagioDrc,
      this.segmento,
      this.turnoDialise});

  factory PacienteResumo.fromJson(Map<String, dynamic> j) => PacienteResumo(
        id: j['id'] as String,
        nome: j['nome'] as String,
        cns: j['cns'] as String?,
        estagioDrc: j['estagio_drc'] as int?,
        segmento: j['segmento'] as String?,
        turnoDialise: j['turno_dialise'] as String?,
      );
}

class PacienteHeader {
  final String id;
  final String nome;
  final String? cns;
  final int? idade;
  final String? sexo;
  final int? estagioDrc;
  final String? etiologiaDrc;
  final String? segmento;
  final String? turnoDialise;
  final List<String> alergias;
  const PacienteHeader({
    required this.id,
    required this.nome,
    this.cns,
    this.idade,
    this.sexo,
    this.estagioDrc,
    this.etiologiaDrc,
    this.segmento,
    this.turnoDialise,
    this.alergias = const [],
  });

  factory PacienteHeader.fromJson(Map<String, dynamic> j) => PacienteHeader(
        id: j['id'] as String,
        nome: j['nome'] as String,
        cns: j['cns'] as String?,
        idade: j['idade'] as int?,
        sexo: j['sexo'] as String?,
        estagioDrc: j['estagio_drc'] as int?,
        etiologiaDrc: j['etiologia_drc'] as String?,
        segmento: j['segmento'] as String?,
        turnoDialise: j['turno_dialise'] as String?,
        alergias: (j['alergias'] as List?)?.cast<String>() ?? const [],
      );
}

class TimelineItem {
  final String tipo; // 'episodio' | 'evolucao' | 'exame'
  final String? subtipo;
  final String titulo;
  final String? detalhe;
  final DateTime data;
  const TimelineItem(
      {required this.tipo,
      this.subtipo,
      required this.titulo,
      this.detalhe,
      required this.data});

  factory TimelineItem.fromJson(Map<String, dynamic> j) => TimelineItem(
        tipo: j['tipo'] as String,
        subtipo: j['subtipo'] as String?,
        titulo: j['titulo'] as String,
        detalhe: j['detalhe'] as String?,
        data: DateTime.parse(j['data'] as String),
      );
}

class Evolucao {
  final String id;
  final String categoria;
  final String? subjetivo, objetivo, avaliacao, plano, textoLivre, resumoIa;
  final DateTime? assinadaEm;
  final DateTime createdAt;
  const Evolucao({
    required this.id,
    required this.categoria,
    this.subjetivo,
    this.objetivo,
    this.avaliacao,
    this.plano,
    this.textoLivre,
    this.resumoIa,
    this.assinadaEm,
    required this.createdAt,
  });

  bool get assinada => assinadaEm != null;

  factory Evolucao.fromJson(Map<String, dynamic> j) => Evolucao(
        id: j['id'] as String,
        categoria: j['categoria'] as String,
        subjetivo: j['subjetivo'] as String?,
        objetivo: j['objetivo'] as String?,
        avaliacao: j['avaliacao'] as String?,
        plano: j['plano'] as String?,
        textoLivre: j['texto_livre'] as String?,
        resumoIa: j['resumo_ia'] as String?,
        assinadaEm: j['assinada_em'] == null
            ? null
            : DateTime.parse(j['assinada_em'] as String),
        createdAt: DateTime.parse(j['created_at'] as String),
      );
}

class PontoExame {
  final DateTime data;
  final double? valor;
  final bool? foraFaixa;
  const PontoExame({required this.data, this.valor, this.foraFaixa});

  factory PontoExame.fromJson(Map<String, dynamic> j) => PontoExame(
        data: DateTime.parse(j['data'] as String),
        valor: (j['valor'] as num?)?.toDouble(),
        foraFaixa: j['fora_faixa'] as bool?,
      );
}

class SerieExame {
  final String codigo;
  final String nome;
  final String? unidade;
  final double? refMin, refMax, ultimoValor;
  final String? tendencia; // 'up' | 'down' | 'flat'
  final List<PontoExame> pontos;
  const SerieExame({
    required this.codigo,
    required this.nome,
    this.unidade,
    this.refMin,
    this.refMax,
    this.ultimoValor,
    this.tendencia,
    this.pontos = const [],
  });

  factory SerieExame.fromJson(Map<String, dynamic> j) => SerieExame(
        codigo: j['codigo'] as String,
        nome: j['nome'] as String,
        unidade: j['unidade'] as String?,
        refMin: (j['ref_min'] as num?)?.toDouble(),
        refMax: (j['ref_max'] as num?)?.toDouble(),
        ultimoValor: (j['ultimo_valor'] as num?)?.toDouble(),
        tendencia: j['tendencia'] as String?,
        pontos: (j['pontos'] as List)
            .map((e) => PontoExame.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
