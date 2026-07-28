import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'lme_models.dart';

/// Acesso às rotas do LME Inteligente.
class LmeRepository {
  final Ref _ref;
  LmeRepository(this._ref);

  Future<List<Laudo>> listar(String pacienteId) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .get('/api/v1/pacientes/$pacienteId/lme');
    return (r.data as List)
        .map((e) => Laudo.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Laudo> gerar(String pacienteId, Map<String, dynamic> body) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/pacientes/$pacienteId/lme', data: body);
    return Laudo.fromJson(r.data as Map<String, dynamic>);
  }

  Future<Laudo> assinar(String laudoId, {String? aceitePor}) async {
    final r = await _ref.read(apiClientProvider).dio.post(
        '/api/v1/lme/$laudoId/assinar',
        data: {if (aceitePor != null) 'aceite_termo_por': aceitePor});
    return Laudo.fromJson(r.data as Map<String, dynamic>);
  }

  Future<Laudo> renovar(String laudoId) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/lme/$laudoId/renovar');
    return Laudo.fromJson(r.data as Map<String, dynamic>);
  }

  /// URL do PDF (aberta no navegador/visualizador com o token atual).
  String pdfUrl(String laudoId) =>
      '${_ref.read(apiClientProvider).dio.options.baseUrl}/api/v1/lme/$laudoId/pdf';

  // ------------------- Assinatura ICP-Brasil (VIDaaS) -------------------

  /// Inicia a autorização no VIDaaS; devolve {state, authorization_url, mock}.
  Future<Map<String, dynamic>> vidaasAutorizar() async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/assinatura/vidaas/autorizacao');
    return r.data as Map<String, dynamic>;
  }

  /// Status da autorização: pendente | autorizada | expirada | erro.
  Future<String> vidaasStatus(String state) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .get('/api/v1/assinatura/vidaas/autorizacao/$state');
    return (r.data as Map<String, dynamic>)['status'] as String;
  }

  /// Assina o PDF do LME com o certificado em nuvem do médico.
  Future<Map<String, dynamic>> vidaasAssinarLme(String laudoId) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/assinatura/vidaas/lme/$laudoId');
    return r.data as Map<String, dynamic>;
  }
}

final lmeRepositoryProvider = Provider<LmeRepository>((ref) => LmeRepository(ref));

final lmesProvider = FutureProvider.family<List<Laudo>, String>(
    (ref, pacienteId) => ref.watch(lmeRepositoryProvider).listar(pacienteId));
