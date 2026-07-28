import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import 'patient_repository.dart';

/// Lista de pacientes da unidade com filtro por segmento de cuidado
/// (Todos · Ambulatório conservador · Hemodiálise) e cadastro de novos.
class PatientsListScreen extends ConsumerStatefulWidget {
  const PatientsListScreen({super.key});

  @override
  ConsumerState<PatientsListScreen> createState() => _PatientsListScreenState();
}

class _PatientsListScreenState extends ConsumerState<PatientsListScreen> {
  String? _segmento; // null = todos

  static const _rotuloSegmento = {
    'conservador': 'Conservador',
    'hemodialise': 'Hemodiálise',
    'dialise_peritoneal': 'DP',
    'transplante': 'Transplante',
  };

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(pacientesProvider(_segmento));
    final c = context.colors;

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('Pacientes'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(pacientesProvider(_segmento)),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        icon: const Icon(Icons.person_add_alt_1_outlined),
        label: const Text('Novo paciente'),
        onPressed: () => context.go('/pacientes/novo'),
      ),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(Gap.lg, Gap.sm, Gap.lg, 0),
          child: Row(children: [
            for (final (rotulo, valor) in [
              ('Todos', null),
              ('Conservador', 'conservador'),
              ('Hemodiálise', 'hemodialise'),
            ]) ...[
              ChoiceChip(
                label: Text(rotulo),
                selected: _segmento == valor,
                onSelected: (_) => setState(() => _segmento = valor),
              ),
              const SizedBox(width: Gap.sm),
            ],
          ]),
        ),
        Expanded(
          child: async.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Text('$e')),
            data: (pacientes) => pacientes.isEmpty
                ? Center(
                    child: Text('Nenhum paciente neste segmento',
                        style: TextStyle(color: c.textSecondary)))
                : ListView.separated(
                    padding: const EdgeInsets.all(Gap.lg),
                    itemCount: pacientes.length,
                    separatorBuilder: (_, __) =>
                        const SizedBox(height: Gap.sm),
                    itemBuilder: (context, i) {
                      final p = pacientes[i];
                      return GlassCard(
                        onTap: () => context.go('/pacientes/${p.id}'),
                        child: Row(
                          children: [
                            CircleAvatar(
                              backgroundColor:
                                  c.primary.withValues(alpha: 0.15),
                              child: Text(p.nome.characters.first,
                                  style: TextStyle(color: c.primary)),
                            ),
                            const SizedBox(width: Gap.lg),
                            Expanded(
                              child: Column(
                                crossAxisAlignment:
                                    CrossAxisAlignment.start,
                                children: [
                                  Text(p.nome,
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleMedium),
                                  Text(
                                    [
                                      if (p.estagioDrc != null)
                                        'DRC estágio ${p.estagioDrc}',
                                      if (p.turnoDialise != null)
                                        p.turnoDialise!,
                                      if (p.cns != null) 'CNS ${p.cns}',
                                    ].join(' · '),
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodySmall
                                        ?.copyWith(color: c.textSecondary),
                                  ),
                                ],
                              ),
                            ),
                            if (p.segmento != null)
                              StatusPill(
                                label: _rotuloSegmento[p.segmento] ??
                                    p.segmento!,
                                status: p.segmento == 'conservador'
                                    ? 'info'
                                    : 'ok',
                              ),
                            const Icon(Icons.chevron_right),
                          ],
                        ),
                      );
                    },
                  ),
          ),
        ),
      ]),
    );
  }
}
