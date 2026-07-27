import 'package:flutter/material.dart';

import 'theme/theme.dart';
import 'widgets/widgets.dart';

void main() => runApp(const NefronApp());

/// Raiz do aplicativo Néfron.
///
/// Tema escuro por padrão, com alternância automática pelo sistema
/// (`ThemeMode.system`). Nesta Etapa 2 a home é uma vitrine do Design System;
/// nas próximas etapas será substituída pelo roteador (go_router) com
/// Autenticação + Dashboard.
class NefronApp extends StatelessWidget {
  const NefronApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Néfron',
      debugShowCheckedModeBanner: false,
      theme: NefronTheme.light(),
      darkTheme: NefronTheme.dark(),
      themeMode: ThemeMode.system,
      home: const _DesignSystemShowcase(),
    );
  }
}

/// Vitrine dos componentes-núcleo — valida os tokens e serve de referência viva.
class _DesignSystemShowcase extends StatelessWidget {
  const _DesignSystemShowcase();

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('néfron·  Design System'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(Gap.lg),
        children: [
          Text('Valores clínicos',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.md),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: Gap.md,
            crossAxisSpacing: Gap.md,
            childAspectRatio: 1.6,
            children: const [
              VitalTile(
                  label: 'Hemoglobina',
                  value: '9.4',
                  unit: 'g/dL',
                  status: 'critical',
                  trend: Trend.down),
              VitalTile(
                  label: 'Kt/V',
                  value: '1.3',
                  status: 'ok',
                  trend: Trend.up),
              VitalTile(
                  label: 'PTH', value: '720', unit: 'pg/mL', status: 'warn'),
              VitalTile(label: 'Peso seco', value: '70.0', unit: 'kg'),
            ],
          ),
          const SizedBox(height: Gap.xl),
          Text('Alertas', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.md),
          GlassCard(
            child: Row(
              children: [
                Icon(Icons.warning_amber_rounded, color: c.warn),
                const SizedBox(width: Gap.md),
                Expanded(
                  child: Text('2 LMEs vencem em 7 dias',
                      style: Theme.of(context).textTheme.bodyLarge),
                ),
                TextButton(onPressed: () {}, child: const Text('Ver')),
              ],
            ),
          ),
          const SizedBox(height: Gap.xl),
          Wrap(
            spacing: Gap.sm,
            runSpacing: Gap.sm,
            children: const [
              StatusPill(label: 'Na meta', status: 'ok'),
              StatusPill(label: 'Atenção', status: 'warn', trend: Trend.up),
              StatusPill(label: 'Crítico', status: 'critical', trend: Trend.down),
              StatusPill(label: 'Info', status: 'info'),
            ],
          ),
          const SizedBox(height: Gap.xl),
          FilledButton(onPressed: () {}, child: const Text('Ação primária')),
        ],
      ),
    );
  }
}
