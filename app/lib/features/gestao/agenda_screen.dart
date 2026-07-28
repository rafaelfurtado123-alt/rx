import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/providers.dart';
import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import '../patients/patient_repository.dart';

/// Agenda/escala de diálise — visão do dia agrupada por turno, com
/// adição de vaga recorrente (turno + dias da semana + máquina).
class AgendaScreen extends ConsumerStatefulWidget {
  const AgendaScreen({super.key});

  @override
  ConsumerState<AgendaScreen> createState() => _AgendaScreenState();
}

final _escalaDiaProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, String>((ref, dataIso) async {
  final r = await ref.watch(apiClientProvider).dio.get('/api/v1/escala/dia',
      queryParameters: {'data': dataIso});
  return r.data as Map<String, dynamic>;
});

class _AgendaScreenState extends ConsumerState<AgendaScreen> {
  DateTime _data = DateTime.now();

  String get _dataIso => DateFormat('yyyy-MM-dd').format(_data);

  @override
  Widget build(BuildContext context) {
    final dia = ref.watch(_escalaDiaProvider(_dataIso));

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(onPressed: () => context.go('/dashboard')),
        title: const Text('Escala de diálise'),
      ),
      floatingActionButton: FloatingActionButton.extended(
        icon: const Icon(Icons.add),
        label: const Text('Nova vaga'),
        onPressed: _abrirNovaVaga,
      ),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.all(Gap.lg),
          child: Row(children: [
            IconButton(
                icon: const Icon(Icons.chevron_left),
                onPressed: () => setState(
                    () => _data = _data.subtract(const Duration(days: 1)))),
            Expanded(
              child: Center(
                child: Text(
                  DateFormat("EEEE, dd 'de' MMMM", 'pt_BR').format(_data),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
            ),
            IconButton(
                icon: const Icon(Icons.chevron_right),
                onPressed: () => setState(
                    () => _data = _data.add(const Duration(days: 1)))),
          ]),
        ),
        Expanded(
          child: dia.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Text('$e')),
            data: (d) {
              final turnos = d['turnos'] as Map<String, dynamic>;
              return ListView(
                padding: const EdgeInsets.symmetric(horizontal: Gap.lg),
                children: [
                  for (final turno in ['manha', 'tarde', 'noite']) ...[
                    _TurnoSection(
                      titulo: const {
                        'manha': 'Manhã',
                        'tarde': 'Tarde',
                        'noite': 'Noite'
                      }[turno]!,
                      vagas:
                          (turnos[turno] as List).cast<Map<String, dynamic>>(),
                    ),
                    const SizedBox(height: Gap.lg),
                  ],
                ],
              );
            },
          ),
        ),
      ]),
    );
  }

  Future<void> _abrirNovaVaga() async {
    final pacientes = await ref.read(patientRepositoryProvider).listar();
    if (!mounted) return;
    final maquina = TextEditingController();
    String? pacienteId;
    String turno = 'manha';
    final dias = <int>{1, 3, 5};
    const nomesDias = ['S', 'T', 'Q', 'Q', 'S', 'S', 'D'];

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
              Text('Nova vaga na escala',
                  style: Theme.of(ctx).textTheme.titleMedium),
              const SizedBox(height: Gap.md),
              DropdownButtonFormField<String>(
                initialValue: pacienteId,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Paciente'),
                items: [
                  for (final p in pacientes)
                    DropdownMenuItem(value: p.id, child: Text(p.nome)),
                ],
                onChanged: (v) => setSheet(() => pacienteId = v),
              ),
              const SizedBox(height: Gap.md),
              DropdownButtonFormField<String>(
                initialValue: turno,
                decoration: const InputDecoration(labelText: 'Turno'),
                items: const [
                  DropdownMenuItem(value: 'manha', child: Text('Manhã')),
                  DropdownMenuItem(value: 'tarde', child: Text('Tarde')),
                  DropdownMenuItem(value: 'noite', child: Text('Noite')),
                ],
                onChanged: (v) => setSheet(() => turno = v ?? 'manha'),
              ),
              const SizedBox(height: Gap.md),
              Text('Dias da semana',
                  style: Theme.of(ctx).textTheme.labelLarge),
              const SizedBox(height: Gap.sm),
              Wrap(spacing: Gap.sm, children: [
                for (var d = 1; d <= 7; d++)
                  FilterChip(
                    label: Text(nomesDias[d - 1]),
                    selected: dias.contains(d),
                    onSelected: (sel) => setSheet(
                        () => sel ? dias.add(d) : dias.remove(d)),
                  ),
              ]),
              const SizedBox(height: Gap.md),
              TextField(
                  controller: maquina,
                  decoration: const InputDecoration(
                      labelText: 'Máquina (opcional, ex.: M03)')),
              const SizedBox(height: Gap.lg),
              FilledButton(
                onPressed: (pacienteId == null || dias.isEmpty)
                    ? null
                    : () async {
                        Navigator.pop(ctx);
                        try {
                          await ref.read(apiClientProvider).dio.post(
                              '/api/v1/pacientes/$pacienteId/escala',
                              data: {
                                'turno': turno,
                                'dias_semana': dias.toList()..sort(),
                                if (maquina.text.isNotEmpty)
                                  'maquina': maquina.text,
                              });
                          ref.invalidate(_escalaDiaProvider(_dataIso));
                        } catch (e) {
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('$e')));
                          }
                        }
                      },
                child: const Text('Adicionar à escala'),
              ),
              const SizedBox(height: Gap.md),
            ],
          ),
        ),
      ),
    );
    maquina.dispose();
  }
}

class _TurnoSection extends StatelessWidget {
  final String titulo;
  final List<Map<String, dynamic>> vagas;
  const _TurnoSection({required this.titulo, required this.vagas});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return GlassCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.schedule, size: 18, color: c.primary),
          const SizedBox(width: Gap.sm),
          Text(titulo, style: Theme.of(context).textTheme.titleMedium),
          const Spacer(),
          StatusPill(label: '${vagas.length}', status: 'info'),
        ]),
        if (vagas.isEmpty) ...[
          const SizedBox(height: Gap.sm),
          Text('Sem pacientes neste turno',
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: c.textSecondary)),
        ],
        for (final v in vagas) ...[
          const SizedBox(height: Gap.sm),
          Row(children: [
            if (v['maquina'] != null) ...[
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: Gap.sm, vertical: 2),
                decoration: BoxDecoration(
                  color: c.primary.withValues(alpha: 0.12),
                  borderRadius: Radii.rSm,
                ),
                child: Text(v['maquina'] as String,
                    style: NefronType.mono(color: c.primary, size: 12)),
              ),
              const SizedBox(width: Gap.md),
            ],
            Expanded(child: Text(v['paciente_nome'] as String? ?? '—')),
          ]),
        ],
      ]),
    );
  }
}
