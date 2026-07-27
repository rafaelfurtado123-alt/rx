import 'package:flutter/material.dart';

import '../theme/nefron_colors.dart';
import '../theme/nefron_spacing.dart';
import '../theme/nefron_typography.dart';
import 'glass_card.dart';
import 'status_pill.dart';

/// Bloco de valor clínico grande: número vital + rótulo + tendência + status.
///
/// Usado nos dashboards e no cabeçalho de exames. O número usa a fonte
/// monoespaçada tabular para leitura rápida à beira-leito.
class VitalTile extends StatelessWidget {
  final String label;
  final String value;
  final String? unit;
  final String? status; // 'ok' | 'warn' | 'critical' | null
  final Trend? trend;
  final VoidCallback? onTap;

  const VitalTile({
    super.key,
    required this.label,
    required this.value,
    this.unit,
    this.status,
    this.trend,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final valueColor = status != null ? c.statusColor(status!) : c.textPrimary;
    return GlassCard(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label,
              style: Theme.of(context)
                  .textTheme
                  .labelLarge
                  ?.copyWith(color: c.textSecondary)),
          const SizedBox(height: Gap.sm),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(value, style: NefronType.vital(valueColor)),
              if (unit != null) ...[
                const SizedBox(width: Gap.xs),
                Text(unit!,
                    style: NefronType.mono(color: c.textSecondary, size: 14)),
              ],
            ],
          ),
          if (status != null) ...[
            const SizedBox(height: Gap.sm),
            StatusPill(label: _statusLabel(status!), status: status!, trend: trend),
          ],
        ],
      ),
    );
  }

  static String _statusLabel(String s) => switch (s) {
        'ok' => 'Na meta',
        'warn' => 'Atenção',
        'critical' => 'Fora da meta',
        _ => 'Info',
      };
}
