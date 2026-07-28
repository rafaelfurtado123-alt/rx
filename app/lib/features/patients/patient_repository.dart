import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'patient_models.dart';

/// Acesso às rotas do prontuário.
class PatientRepository {
  final Ref _ref;
  PatientRepository(this._ref);

  Future<List<PacienteResumo>> listar({String? segmento}) async {
    final r = await _ref.read(apiClientProvider).dio.get('/api/v1/pacientes',
        queryParameters: {if (segmento != null) 'segmento': segmento});
    return (r.data as List)
        .map((e) => PacienteResumo.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<PacienteHeader> criar(Map<String, dynamic> body) async {
    final r =
        await _ref.read(apiClientProvider).dio.post('/api/v1/pacientes', data: body);
    return PacienteHeader.fromJson(r.data as Map<String, dynamic>);
  }

  Future<PacienteHeader> atualizar(String id, Map<String, dynamic> body) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .patch('/api/v1/pacientes/$id', data: body);
    return PacienteHeader.fromJson(r.data as Map<String, dynamic>);
  }

  Future<PacienteHeader> header(String id) async {
    final r = await _ref.read(apiClientProvider).dio.get('/api/v1/pacientes/$id');
    return PacienteHeader.fromJson(r.data as Map<String, dynamic>);
  }

  Future<List<TimelineItem>> timeline(String id) async {
    final r =
        await _ref.read(apiClientProvider).dio.get('/api/v1/pacientes/$id/timeline');
    return (r.data as List)
        .map((e) => TimelineItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<Evolucao>> evolucoes(String id) async {
    final r =
        await _ref.read(apiClientProvider).dio.get('/api/v1/pacientes/$id/evolucoes');
    return (r.data as List)
        .map((e) => Evolucao.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Evolucao> criarEvolucao(String id, Map<String, dynamic> body) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/pacientes/$id/evolucoes', data: body);
    return Evolucao.fromJson(r.data as Map<String, dynamic>);
  }

  Future<String> resumoIa(String id, Map<String, dynamic> soap) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .post('/api/v1/pacientes/$id/evolucoes/resumo-ia', data: soap);
    return (r.data as Map<String, dynamic>)['resumo'] as String;
  }

  Future<SerieExame> serie(String id, String codigo) async {
    final r = await _ref
        .read(apiClientProvider)
        .dio
        .get('/api/v1/pacientes/$id/exames/$codigo');
    return SerieExame.fromJson(r.data as Map<String, dynamic>);
  }
}

final patientRepositoryProvider =
    Provider<PatientRepository>((ref) => PatientRepository(ref));

/// Lista de pacientes; `null` = todos os segmentos.
final pacientesProvider =
    FutureProvider.family<List<PacienteResumo>, String?>(
        (ref, segmento) =>
            ref.watch(patientRepositoryProvider).listar(segmento: segmento));

final pacienteHeaderProvider = FutureProvider.family<PacienteHeader, String>(
    (ref, id) => ref.watch(patientRepositoryProvider).header(id));

final timelineProvider = FutureProvider.family<List<TimelineItem>, String>(
    (ref, id) => ref.watch(patientRepositoryProvider).timeline(id));

final evolucoesProvider = FutureProvider.family<List<Evolucao>, String>(
    (ref, id) => ref.watch(patientRepositoryProvider).evolucoes(id));

final serieExameProvider =
    FutureProvider.family<SerieExame, ({String pacienteId, String codigo})>(
        (ref, arg) =>
            ref.watch(patientRepositoryProvider).serie(arg.pacienteId, arg.codigo));
