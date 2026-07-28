/// Modelos do LME Inteligente (espelham os DTOs do FastAPI).

class ExameChecagem {
  final String codigo;
  final String nome;
  final bool obrigatorio;
  final String situacao; // 'presente' | 'ausente' | 'vencido'
  final double? valor;
  final String? unidade;
  final DateTime? dataColeta;
  const ExameChecagem({
    required this.codigo,
    required this.nome,
    this.obrigatorio = true,
    required this.situacao,
    this.valor,
    this.unidade,
    this.dataColeta,
  });

  factory ExameChecagem.fromJson(Map<String, dynamic> j) => ExameChecagem(
        codigo: j['codigo'] as String,
        nome: j['nome'] as String,
        obrigatorio: j['obrigatorio'] as bool? ?? true,
        situacao: j['situacao'] as String,
        valor: (j['valor'] as num?)?.toDouble(),
        unidade: j['unidade'] as String?,
        dataColeta: j['data_coleta'] == null
            ? null
            : DateTime.parse(j['data_coleta'] as String),
      );
}

class Laudo {
  final String id;
  final String status;
  final String medicamento;
  final String? posologia;
  final double? quantidadeMes;
  final String? pcdtNome, pcdtVersao;
  final String? cidPrincipal;
  final List<String> cidsSecundarios;
  final String? anamnese, justificativa;
  final List<ExameChecagem> exames;
  final List<String> pendencias;
  final DateTime? emitidoEm, validoAte;
  final int? diasRestantes;
  final String? laudoAnteriorId;
  const Laudo({
    required this.id,
    required this.status,
    required this.medicamento,
    this.posologia,
    this.quantidadeMes,
    this.pcdtNome,
    this.pcdtVersao,
    this.cidPrincipal,
    this.cidsSecundarios = const [],
    this.anamnese,
    this.justificativa,
    this.exames = const [],
    this.pendencias = const [],
    this.emitidoEm,
    this.validoAte,
    this.diasRestantes,
    this.laudoAnteriorId,
  });

  bool get podeEmitir => pendencias.isEmpty && status == 'rascunho';
  bool get vigente => status == 'vigente';

  factory Laudo.fromJson(Map<String, dynamic> j) => Laudo(
        id: j['id'] as String,
        status: j['status'] as String,
        medicamento: j['medicamento'] as String,
        posologia: j['posologia'] as String?,
        quantidadeMes: (j['quantidade_mes'] as num?)?.toDouble(),
        pcdtNome: j['pcdt_nome'] as String?,
        pcdtVersao: j['pcdt_versao'] as String?,
        cidPrincipal: j['cid_principal'] as String?,
        cidsSecundarios:
            (j['cids_secundarios'] as List?)?.cast<String>() ?? const [],
        anamnese: j['anamnese'] as String?,
        justificativa: j['justificativa'] as String?,
        exames: ((j['exames'] as List?) ?? const [])
            .map((e) => ExameChecagem.fromJson(e as Map<String, dynamic>))
            .toList(),
        pendencias: (j['pendencias'] as List?)?.cast<String>() ?? const [],
        emitidoEm: j['emitido_em'] == null
            ? null
            : DateTime.parse(j['emitido_em'] as String),
        validoAte: j['valido_ate'] == null
            ? null
            : DateTime.parse(j['valido_ate'] as String),
        diasRestantes: j['dias_restantes'] as int?,
        laudoAnteriorId: j['laudo_anterior_id'] as String?,
      );
}
