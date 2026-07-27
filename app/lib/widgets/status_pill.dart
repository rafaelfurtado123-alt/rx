import 'package:flutter/material.dart';

import '../theme/nefron_colors.dart';
import '../theme/nefron_spacing.dart';

/// Direção da tendência de um valor clínico.
enum Trend { up, down, flat }

/// Chip de status clínico (ok / warn / critical / info).
///
/// A cor NUNCA é o único sinal: sempre há ícone + rótulo, garantindo leitura
/// por usuários com daltonismo (princípio de acessibilidade do DS).
class StatusPill extends StatelessWidget {
  final String label;
  final String status; // 'ok' | 'warn' | 'critical' | 'info'
  final Trend? trend;

  const StatusPill({
    super.key,
    required this.label,
    required this.status,
    this.trend,
  });

  IconData get _icon => switch (status) {
        'ok' => Icons.check_circle_outline,
        'warn' => Icons.warning_amber_rounded,
        'critical' => Icons.error_outline,
        _ => Icons.info_outline,
      };

  IconData? get _trendIcon => switch (trend) {
        Trend.up => Icons.arrow_upward,
        Trend.down => Icons.arrow_downward,
        Trend.flat => Icons.remove,
        null => null,
      };

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final color = c.statusColor(status);
    return Semantics(
      label: 'Status $label',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: Gap.md, vertical: Gap.xs),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.14),
          borderRadius: const BorderRadius.all(Radius.circular(Radii.pill)),
          border: Border.all(color: color.withValues(alpha: 0.4)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(_icon, size: 14, color: color),
            const SizedBox(width: Gap.xs),
            Text(
              label,
              style: Theme.of(context)
                  .textTheme
                  .labelLarge
                  ?.copyWith(color: color),
            ),
            if (_trendIcon != null) ...[
              const SizedBox(width: 2),
              Icon(_trendIcon, size: 13, color: color),
            ],
          ],
        ),
      ),
    );
  }
}
