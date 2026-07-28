import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import 'auth_controller.dart';

/// Seleção de vínculo (unidade + papel) quando o profissional atua em mais de um.
class SelectContextScreen extends ConsumerWidget {
  const SelectContextScreen({super.key});

  static const _papelLabel = {
    'medico': 'Médico',
    'enfermeiro': 'Enfermeiro',
    'tecnico': 'Técnico',
    'administrativo': 'Administrativo',
    'admin': 'Administrador',
    'auditor': 'Auditor',
    'equipe_multi': 'Equipe multiprofissional',
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('Selecione a unidade'),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: ListView.separated(
            shrinkWrap: true,
            padding: const EdgeInsets.all(Gap.xl),
            itemCount: auth.vinculos.length,
            separatorBuilder: (_, __) => const SizedBox(height: Gap.md),
            itemBuilder: (context, i) {
              final v = auth.vinculos[i];
              return GlassCard(
                onTap: auth.loading
                    ? null
                    : () => ref
                        .read(authControllerProvider.notifier)
                        .selectContext(v.unidadeId, v.papel),
                child: Row(
                  children: [
                    Icon(Icons.local_hospital_outlined,
                        color: context.colors.primary),
                    const SizedBox(width: Gap.lg),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(v.unidadeNome,
                              style: Theme.of(context).textTheme.titleMedium),
                          Text(_papelLabel[v.papel] ?? v.papel,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(color: context.colors.textSecondary)),
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
      ),
    );
  }
}
