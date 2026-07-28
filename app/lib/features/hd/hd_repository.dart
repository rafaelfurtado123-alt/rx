import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'hd_models.dart';

/// Acesso às rotas de prescrição de HD e sessão.
class HdRepository {
  final Ref _ref;
  HdRepository(this._ref);

  Future<List<AcessoVascular>> acessos(String pacienteId) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .get('/api/v1/pacientes/$pacienteId/acessos');
    return (r.data as List)
        .map((e) => AcessoVascular.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<AcessoVascular> criarAcesso(
      String pacienteId, Map<String, dynamic> body) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/pacientes/$pacienteId/acessos', data: body);
    return AcessoVascular.fromJson(r.data as Map<String, dynamic>);
  }

  Future<List<PrescricaoHD>> prescricoesHd(String pacienteId) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .get('/api/v1/pacientes/$pacienteId/prescricoes-hd');
    return (r.data as List)
        .map((e) => PrescricaoHD.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<PrescricaoHD> criarPrescricaoHd(
      String pacienteId, Map<String, dynamic> body) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/pacientes/$pacienteId/prescricoes-hd', data: body);
    return PrescricaoHD.fromJson(r.data as Map<String, dynamic>);
  }

  Future<List<SessaoHD>> sessoes(String pacienteId) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .get('/api/v1/pacientes/$pacienteId/sessoes');
    return (r.data as List)
        .map((e) => SessaoHD.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<SessaoHD> recepcao(String pacienteId, Map<String, dynamic> body) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/pacientes/$pacienteId/sessoes', data: body);
    return SessaoHD.fromJson(r.data as Map<String, dynamic>);
  }

  Future<SessaoHD> iniciar(String sessaoId, {String? maquina}) async {
    final r = await _ref.read(apiClientProvider).dio.post(
        '/api/v1/sessoes/$sessaoId/iniciar',
        queryParameters: {if (maquina != null) 'maquina': maquina});
    return SessaoHD.fromJson(r.data as Map<String, dynamic>);
  }

  Future<void> registrarParametro(
      String sessaoId, Map<String, dynamic> body) async {
    await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/sessoes/$sessaoId/parametros', data: body);
  }

  Future<void> registrarIntercorrencia(
      String sessaoId, Map<String, dynamic> body) async {
    await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/sessoes/$sessaoId/intercorrencias', data: body);
  }

  Future<SessaoHD> encerrar(String sessaoId, Map<String, dynamic> body) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/sessoes/$sessaoId/encerrar', data: body);
    return SessaoHD.fromJson(r.data as Map<String, dynamic>);
  }
}

final hdRepositoryProvider = Provider<HdRepository>((ref) => HdRepository(ref));

final acessosProvider = FutureProvider.family<List<AcessoVascular>, String>(
    (ref, id) => ref.watch(hdRepositoryProvider).acessos(id));

final prescricoesHdProvider = FutureProvider.family<List<PrescricaoHD>, String>(
    (ref, id) => ref.watch(hdRepositoryProvider).prescricoesHd(id));

final sessoesProvider = FutureProvider.family<List<SessaoHD>, String>(
    (ref, id) => ref.watch(hdRepositoryProvider).sessoes(id));
