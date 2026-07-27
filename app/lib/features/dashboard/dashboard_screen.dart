import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import '../auth/auth_controller.dart';
import 'dashboard_models.dart';
import 'dashboard_repository.dart';

/// Dashboard por perfil. As métricas e alertas vêm da API conforme o papel ativo.
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(dashboardProvider);
    final papel = ref.watch(authControllerProvider).papel ?? '';

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Row(
          children: [
            const Text('néfron·'),
            const SizedBox(width: Gap.md),
            _RoleChip(papel: papel),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.people_outline),
            tooltip: 'Pacientes',
            onPressed: () => context.go('/pacientes'),
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(dashboardProvider),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sair',
            onPressed: () => ref.read(authControllerProvider.notifier).logout(),
          ),
        ],
      ),
      body: async.when(
        loading: () => const _DashboardSkeleton(),
        error: (e, _) => _ErrorState(
          message: '$e',
          onRetry: () => ref.invalidate(dashboardProvider),
        ),
        data: (dash) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(dashboardProvider),
          child: ListView(
            padding: const EdgeInsets.all(Gap.lg),
            children: [
              Text(dash.saudacao, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: Gap.lg),
              if (dash.alertas.isNotEmpty) ...[
                ...dash.alertas.map((a) => Padding(
                      padding: const EdgeInsets.only(bottom: Gap.sm),
                      child: _AlertBanner(alerta: a),
                    )),
                const SizedBox(height: Gap.md),
              ],
              _MetricsGrid(metricas: dash.metricas),
            ],
          ),
        ),
      ),
    );
  }
}

class _RoleChip extends StatelessWidget {
  final String papel;
  const _RoleChip({required this.papel});
  static const _label = {
    'medico': 'Médico',
    'enfermeiro': 'Enfermeiro',
    'tecnico': 'Técnico',
    'administrativo': 'Administrativo',
  };
  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: Gap.md, vertical: 2),
      decoration: BoxDecoration(
        color: c.primary.withValues(alpha: 0.15),
        borderRadius: const BorderRadius.all(Radius.circular(Radii.pill)),
      ),
      child: Text(_label[papel] ?? papel,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(color: c.primary)),
    );
  }
}

class _MetricsGrid extends StatelessWidget {
  final List<MetricCard> metricas;
  const _MetricsGrid({required this.metricas});
  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      final cols = constraints.maxWidth > 700 ? 4 : 2;
      return GridView.count(
        crossAxisCount: cols,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: Gap.md,
        crossAxisSpacing: Gap.md,
        childAspectRatio: 1.5,
        children: metricas
            .map((m) => VitalTile(
                  label: m.titulo,
                  value: m.valor,
                  status: m.status,
                ))
            .toList(),
      );
    });
  }
}

class _AlertBanner extends StatelessWidget {
  final AlertaProativo alerta;
  const _AlertBanner({required this.alerta});
  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final color = c.statusColor(alerta.nivel);
    return GlassCard(
      child: Row(
        children: [
          Icon(
              alerta.nivel == 'critical'
                  ? Icons.error_outline
                  : Icons.warning_amber_rounded,
              color: color),
          const SizedBox(width: Gap.md),
          Expanded(
              child: Text(alerta.texto,
                  style: Theme.of(context).textTheme.bodyLarge)),
        ],
      ),
    );
  }
}

class _DashboardSkeleton extends StatelessWidget {
  const _DashboardSkeleton();
  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 2,
      padding: const EdgeInsets.all(Gap.lg),
      mainAxisSpacing: Gap.md,
      crossAxisSpacing: Gap.md,
      childAspectRatio: 1.5,
      children: List.generate(
        4,
        (_) => GlassCard(
            child: Center(
                child: CircularProgressIndicator(
                    color: context.colors.primary, strokeWidth: 2))),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorState({required this.message, required this.onRetry});
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.cloud_off, size: 40, color: context.colors.textSecondary),
          const SizedBox(height: Gap.md),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: Gap.lg),
          FilledButton(onPressed: onRetry, child: const Text('Tentar novamente')),
        ],
      ),
    );
  }
}
