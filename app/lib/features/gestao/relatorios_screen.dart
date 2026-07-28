import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../theme/theme.dart';
import '../../widgets/widgets.dart';

/// Relatórios da unidade: censo + indicadores de qualidade (ANVISA/PCDT).
class RelatoriosScreen extends ConsumerWidget {
  const RelatoriosScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final censo = ref.watch(_censoProvider);
    final indicadores = ref.watch(_indicadoresProvider);

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(onPressed: () => context.go('/dashboard')),
        title: const Text('Relatórios e indicadores'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.invalidate(_censoProvider);
              ref.invalidate(_indicadoresProvider);
            },
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(Gap.lg),
        children: [
          Text('Censo da unidade',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.md),
          censo.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Text('$e'),
            data: (c) => GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: Gap.md,
              crossAxisSpacing: Gap.md,
              childAspectRatio: 1.7,
              children: [
                VitalTile(
                    label: 'Pacientes ativos',
                    value: '${c['pacientes_ativos']}'),
                VitalTile(
                    label: 'Em escala de HD', value: '${c['em_escala_hd']}'),
                VitalTile(
                    label: 'Sessões (30 dias)', value: '${c['sessoes_30d']}'),
                VitalTile(
                    label: 'Intercorrências (30d)',
                    value: '${c['intercorrencias_30d']}',
                    status: (c['intercorrencias_30d'] as int) > 0
                        ? 'warn'
                        : 'ok'),
              ],
            ),
          ),
          const SizedBox(height: Gap.xl),
          Text('Indicadores de qualidade (90 dias)',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.md),
          indicadores.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Text('$e'),
            data: (ind) => Column(children: [
              for (final i
                  in (ind['indicadores'] as List).cast<Map<String, dynamic>>())
                Padding(
                  padding: const EdgeInsets.only(bottom: Gap.sm),
                  child: _IndicadorCard(indicador: i),
                ),
            ]),
          ),
        ],
      ),
    );
  }
}

final _censoProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
    (ref) async {
  final r =
      await ref.watch(apiClientProvider).dio.get('/api/v1/relatorios/censo');
  return r.data as Map<String, dynamic>;
});

final _indicadoresProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
    (ref) async {
  final r = await ref
      .watch(apiClientProvider)
      .dio
      .get('/api/v1/relatorios/indicadores');
  return r.data as Map<String, dynamic>;
});

class _IndicadorCard extends StatelessWidget {
  final Map<String, dynamic> indicador;
  const _IndicadorCard({required this.indicador});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final valor = indicador['valor'] as num?;
    final status = indicador['status'] as String?;
    final unidade = indicador['unidade'] as String? ?? '%';
    return GlassCard(
      child: Row(children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(indicador['titulo'] as String,
                style: Theme.of(context).textTheme.bodyLarge),
            Text(
              'Meta: ${indicador['meta'] ?? '—'} · '
              '${indicador['numerador']}/${indicador['denominador']}',
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: c.textSecondary),
            ),
          ]),
        ),
        Text(
          valor == null ? '—' : '$valor$unidade',
          style: NefronType.mono(
              color: status == null
                  ? c.textPrimary
                  : c.statusColor(status),
              size: 20,
              weight: FontWeight.w700),
        ),
      ]),
    );
  }
}
