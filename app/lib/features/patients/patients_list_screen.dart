import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import 'patient_repository.dart';

/// Lista de pacientes da unidade ativa (isolada por RLS).
class PatientsListScreen extends ConsumerWidget {
  const PatientsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(pacientesProvider);
    final c = context.colors;

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('Pacientes'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(pacientesProvider),
          ),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (pacientes) => pacientes.isEmpty
            ? Center(
                child: Text('Nenhum paciente na unidade',
                    style: TextStyle(color: c.textSecondary)))
            : ListView.separated(
                padding: const EdgeInsets.all(Gap.lg),
                itemCount: pacientes.length,
                separatorBuilder: (_, __) => const SizedBox(height: Gap.sm),
                itemBuilder: (context, i) {
                  final p = pacientes[i];
                  return GlassCard(
                    onTap: () => context.go('/pacientes/${p.id}'),
                    child: Row(
                      children: [
                        CircleAvatar(
                          backgroundColor: c.primary.withValues(alpha: 0.15),
                          child: Text(p.nome.characters.first,
                              style: TextStyle(color: c.primary)),
                        ),
                        const SizedBox(width: Gap.lg),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(p.nome,
                                  style: Theme.of(context).textTheme.titleMedium),
                              Text(
                                [
                                  if (p.estagioDrc != null) 'DRC estágio ${p.estagioDrc}',
                                  if (p.turnoDialise != null) p.turnoDialise!,
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
                        const Icon(Icons.chevron_right),
                      ],
                    ),
                  );
                },
              ),
      ),
    );
  }
}
