/// Modelos do dashboard (espelham os DTOs do FastAPI).

class MetricCard {
  final String chave;
  final String titulo;
  final String valor;
  final String? status; // 'ok' | 'warn' | 'critical' | null
  const MetricCard(
      {required this.chave, required this.titulo, required this.valor, this.status});

  factory MetricCard.fromJson(Map<String, dynamic> j) => MetricCard(
        chave: j['chave'] as String,
        titulo: j['titulo'] as String,
        valor: '${j['valor']}',
        status: j['status'] as String?,
      );
}

class AlertaProativo {
  final String nivel; // 'warn' | 'critical'
  final String texto;
  final int? quantidade;
  const AlertaProativo({required this.nivel, required this.texto, this.quantidade});

  factory AlertaProativo.fromJson(Map<String, dynamic> j) => AlertaProativo(
        nivel: j['nivel'] as String,
        texto: j['texto'] as String,
        quantidade: j['quantidade'] as int?,
      );
}

class Dashboard {
  final String perfil;
  final String saudacao;
  final List<MetricCard> metricas;
  final List<AlertaProativo> alertas;
  const Dashboard({
    required this.perfil,
    required this.saudacao,
    required this.metricas,
    required this.alertas,
  });

  factory Dashboard.fromJson(Map<String, dynamic> j) => Dashboard(
        perfil: j['perfil'] as String,
        saudacao: j['saudacao'] as String,
        metricas: (j['metricas'] as List)
            .map((e) => MetricCard.fromJson(e as Map<String, dynamic>))
            .toList(),
        alertas: (j['alertas'] as List)
            .map((e) => AlertaProativo.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
