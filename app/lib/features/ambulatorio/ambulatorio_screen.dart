import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/providers.dart';
import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import '../patients/patient_repository.dart';

/// Ambulatório conservador: painel da população DRC sem TRS + agenda do dia
/// (consultas com fechamento realizada/faltou) + agendamento.
class AmbulatorioScreen extends ConsumerStatefulWidget {
  const AmbulatorioScreen({super.key});

  @override
  ConsumerState<AmbulatorioScreen> createState() => _AmbulatorioScreenState();
}

final _painelProvider =
    FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final r =
      await ref.watch(apiClientProvider).dio.get('/api/v1/ambulatorio/painel');
  return r.data as Map<String, dynamic>;
});

final _agendaDiaProvider = FutureProvider.autoDispose
    .family<List<Map<String, dynamic>>, String>((ref, dataIso) async {
  final r = await ref.watch(apiClientProvider).dio.get(
      '/api/v1/ambulatorio/consultas',
      queryParameters: {'data': dataIso});
  return (r.data as List).cast<Map<String, dynamic>>();
});

class _AmbulatorioScreenState extends ConsumerState<AmbulatorioScreen> {
  DateTime _data = DateTime.now();
  bool _busy = false;

  String get _dataIso => DateFormat('yyyy-MM-dd').format(_data);

  void _refresh() {
    ref.invalidate(_painelProvider);
    ref.invalidate(_agendaDiaProvider(_dataIso));
  }

  Future<void> _fecharConsulta(String id, String status) async {
    setState(() => _busy = true);
    try {
      await ref
          .read(apiClientProvider)
          .dio
          .post('/api/v1/consultas/$id/status', data: {'status': status});
      _refresh();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final painel = ref.watch(_painelProvider);
    final agenda = ref.watch(_agendaDiaProvider(_dataIso));

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(onPressed: () => context.go('/dashboard')),
        title: const Text('Ambulatório conservador'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _refresh),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        icon: const Icon(Icons.event_available_outlined),
        label: const Text('Agendar consulta'),
        onPressed: _busy ? null : _abrirAgendamento,
      ),
      body: ListView(
        padding: const EdgeInsets.all(Gap.lg),
        children: [
          painel.when(
            loading: () => const LinearProgressIndicator(),
            error: (e, _) => Text('$e'),
            data: (p) => GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: Gap.md,
              crossAxisSpacing: Gap.md,
              childAspectRatio: 1.7,
              children: [
                VitalTile(
                    label: 'Pacientes conservador',
                    value: '${p['pacientes_conservador']}'),
                VitalTile(
                    label: 'Consultas hoje', value: '${p['consultas_hoje']}'),
                VitalTile(
                    label: 'Consultas na semana',
                    value: '${p['consultas_semana']}'),
                VitalTile(
                    label: 'Preparo TRS (E4–E5)',
                    value: '${p['candidatos_preparo_trs']}',
                    status: (p['candidatos_preparo_trs'] as int) > 0
                        ? 'warn'
                        : 'ok'),
              ],
            ),
          ),
          const SizedBox(height: Gap.lg),
          Row(children: [
            IconButton(
                icon: const Icon(Icons.chevron_left),
                onPressed: () => setState(
                    () => _data = _data.subtract(const Duration(days: 1)))),
            Expanded(
              child: Center(
                child: Text(
                  DateFormat("EEEE, dd/MM", 'pt_BR').format(_data),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
            ),
            IconButton(
                icon: const Icon(Icons.chevron_right),
                onPressed: () => setState(
                    () => _data = _data.add(const Duration(days: 1)))),
          ]),
          agenda.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Text('$e'),
            data: (consultas) => consultas.isEmpty
                ? Padding(
                    padding: const EdgeInsets.all(Gap.xl),
                    child: Center(
                        child: Text('Sem consultas neste dia',
                            style: TextStyle(color: c.textSecondary))),
                  )
                : Column(children: [
                    for (final consulta in consultas) ...[
                      _ConsultaCard(
                        consulta: consulta,
                        busy: _busy,
                        onRealizada: () => _fecharConsulta(
                            consulta['id'] as String, 'realizada'),
                        onFaltou: () => _fecharConsulta(
                            consulta['id'] as String, 'faltou'),
                      ),
                      const SizedBox(height: Gap.sm),
                    ],
                  ]),
          ),
          const SizedBox(height: Gap.huge),
        ],
      ),
    );
  }

  Future<void> _abrirAgendamento() async {
    final pacientes = await ref
        .read(patientRepositoryProvider)
        .listar(segmento: 'conservador');
    if (!mounted) return;

    String? pacienteId;
    String tipo = 'retorno';
    TimeOfDay hora = const TimeOfDay(hour: 9, minute: 0);
    DateTime dia = _data;

    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) => Padding(
          padding: EdgeInsets.only(
              left: Gap.lg,
              right: Gap.lg,
              bottom: MediaQuery.of(ctx).viewInsets.bottom + Gap.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Agendar consulta',
                  style: Theme.of(ctx).textTheme.titleMedium),
              const SizedBox(height: Gap.md),
              DropdownButtonFormField<String>(
                initialValue: pacienteId,
                isExpanded: true,
                decoration: const InputDecoration(
                    labelText: 'Paciente (ambulatório conservador)'),
                items: [
                  for (final p in pacientes)
                    DropdownMenuItem(value: p.id, child: Text(p.nome)),
                ],
                onChanged: (v) => setSheet(() => pacienteId = v),
              ),
              const SizedBox(height: Gap.md),
              DropdownButtonFormField<String>(
                initialValue: tipo,
                decoration: const InputDecoration(labelText: 'Tipo'),
                items: const [
                  DropdownMenuItem(
                      value: 'primeira_consulta',
                      child: Text('Primeira consulta')),
                  DropdownMenuItem(value: 'retorno', child: Text('Retorno')),
                  DropdownMenuItem(
                      value: 'preparo_trs', child: Text('Preparo para TRS')),
                ],
                onChanged: (v) => setSheet(() => tipo = v ?? 'retorno'),
              ),
              const SizedBox(height: Gap.md),
              Row(children: [
                Expanded(
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.event, size: 16),
                    label: Text(DateFormat('dd/MM/yyyy').format(dia)),
                    onPressed: () async {
                      final d = await showDatePicker(
                        context: ctx,
                        firstDate: DateTime.now()
                            .subtract(const Duration(days: 1)),
                        lastDate:
                            DateTime.now().add(const Duration(days: 365)),
                        initialDate: dia,
                      );
                      if (d != null) setSheet(() => dia = d);
                    },
                  ),
                ),
                const SizedBox(width: Gap.md),
                Expanded(
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.schedule, size: 16),
                    label: Text(hora.format(ctx)),
                    onPressed: () async {
                      final h = await showTimePicker(
                          context: ctx, initialTime: hora);
                      if (h != null) setSheet(() => hora = h);
                    },
                  ),
                ),
              ]),
              const SizedBox(height: Gap.lg),
              FilledButton(
                onPressed: pacienteId == null
                    ? null
                    : () async {
                        Navigator.pop(ctx);
                        final dataHora = DateTime.utc(dia.year, dia.month,
                            dia.day, hora.hour, hora.minute);
                        try {
                          await ref.read(apiClientProvider).dio.post(
                              '/api/v1/pacientes/$pacienteId/consultas',
                              data: {
                                'data_hora': dataHora.toIso8601String(),
                                'tipo': tipo,
                              });
                          _refresh();
                        } catch (e) {
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('$e')));
                          }
                        }
                      },
                child: const Text('Agendar'),
              ),
              const SizedBox(height: Gap.md),
            ],
          ),
        ),
      ),
    );
  }
}

class _ConsultaCard extends StatelessWidget {
  final Map<String, dynamic> consulta;
  final bool busy;
  final VoidCallback onRealizada;
  final VoidCallback onFaltou;
  const _ConsultaCard(
      {required this.consulta,
      required this.busy,
      required this.onRealizada,
      required this.onFaltou});

  static const _tipoRotulo = {
    'primeira_consulta': '1ª consulta',
    'retorno': 'Retorno',
    'preparo_trs': 'Preparo TRS',
  };

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final hora = DateFormat('HH:mm')
        .format(DateTime.parse(consulta['data_hora'] as String).toLocal());
    final status = consulta['status'] as String;
    final aberta = status == 'agendada';

    return GlassCard(
      child: Row(children: [
        Text(hora, style: NefronType.mono(color: c.primary, size: 18)),
        const SizedBox(width: Gap.lg),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(consulta['paciente_nome'] as String? ?? '—',
                style: Theme.of(context).textTheme.titleMedium),
            Text(_tipoRotulo[consulta['tipo']] ?? consulta['tipo'] as String,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: c.textSecondary)),
          ]),
        ),
        if (aberta) ...[
          IconButton(
            tooltip: 'Realizada',
            icon: Icon(Icons.check_circle_outline, color: c.ok),
            onPressed: busy ? null : onRealizada,
          ),
          IconButton(
            tooltip: 'Faltou',
            icon: Icon(Icons.person_off_outlined, color: c.warn),
            onPressed: busy ? null : onFaltou,
          ),
        ] else
          StatusPill(
            label: status,
            status: switch (status) {
              'realizada' => 'ok',
              'faltou' => 'warn',
              _ => 'info',
            },
          ),
      ]),
    );
  }
}
