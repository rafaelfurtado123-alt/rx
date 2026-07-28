import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../features/patients/patient_models.dart';
import '../theme/theme.dart';
import 'glass_card.dart';
import 'status_pill.dart';

/// Gráfico de tendência de um exame com faixa-meta sombreada e destaque dos
/// pontos fora da faixa. Usa fl_chart. Base dos gráficos evolutivos (Hb, PTH...).
class TrendChart extends StatelessWidget {
  final SerieExame serie;
  const TrendChart({super.key, required this.serie});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final pontos = serie.pontos.where((p) => p.valor != null).toList();

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '${serie.nome}${serie.unidade != null ? ' (${serie.unidade})' : ''}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              if (serie.ultimoValor != null)
                StatusPill(
                  label: _fmt(serie.ultimoValor!),
                  status: _statusUltimo(),
                  trend: switch (serie.tendencia) {
                    'up' => Trend.up,
                    'down' => Trend.down,
                    'flat' => Trend.flat,
                    _ => null,
                  },
                ),
            ],
          ),
          const SizedBox(height: Gap.lg),
          SizedBox(
            height: 200,
            child: pontos.length < 2
                ? Center(
                    child: Text('Dados insuficientes para o gráfico',
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: c.textSecondary)))
                : LineChart(_data(context, pontos)),
          ),
          if (serie.refMin != null || serie.refMax != null) ...[
            const SizedBox(height: Gap.sm),
            Text(
              'Faixa-meta: ${serie.refMin ?? '−'} a ${serie.refMax ?? '−'} ${serie.unidade ?? ''}',
              style:
                  Theme.of(context).textTheme.bodySmall?.copyWith(color: c.textSecondary),
            ),
          ],
        ],
      ),
    );
  }

  String _statusUltimo() {
    final v = serie.ultimoValor;
    if (v == null) return 'info';
    if (serie.refMin != null && v < serie.refMin!) return 'critical';
    if (serie.refMax != null && v > serie.refMax!) return 'critical';
    return 'ok';
  }

  LineChartData _data(BuildContext context, List<PontoExame> pontos) {
    final c = context.colors;
    final spots = <FlSpot>[];
    for (var i = 0; i < pontos.length; i++) {
      spots.add(FlSpot(i.toDouble(), pontos[i].valor!));
    }
    final valores = pontos.map((p) => p.valor!).toList();
    var minY = valores.reduce((a, b) => a < b ? a : b);
    var maxY = valores.reduce((a, b) => a > b ? a : b);
    if (serie.refMin != null) minY = minY < serie.refMin! ? minY : serie.refMin!;
    if (serie.refMax != null) maxY = maxY > serie.refMax! ? maxY : serie.refMax!;
    final pad = (maxY - minY).abs() * 0.15 + 0.5;

    return LineChartData(
      minY: minY - pad,
      maxY: maxY + pad,
      gridData: const FlGridData(show: true, drawVerticalLine: false),
      titlesData: const FlTitlesData(
        topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        leftTitles: AxisTitles(
            sideTitles: SideTitles(showTitles: true, reservedSize: 36)),
      ),
      borderData: FlBorderData(show: false),
      // Faixa-meta sombreada (entre refMin e refMax)
      rangeAnnotations: RangeAnnotations(
        horizontalRangeAnnotations: [
          if (serie.refMin != null && serie.refMax != null)
            HorizontalRangeAnnotation(
              y1: serie.refMin!,
              y2: serie.refMax!,
              color: c.ok.withValues(alpha: 0.12),
            ),
        ],
      ),
      lineBarsData: [
        LineChartBarData(
          spots: spots,
          isCurved: true,
          barWidth: 3,
          color: c.primary,
          dotData: FlDotData(
            show: true,
            getDotPainter: (spot, _, __, ___) {
              final p = pontos[spot.x.toInt()];
              final fora = p.foraFaixa ?? false;
              return FlDotCirclePainter(
                radius: 4,
                color: fora ? c.critical : c.primary,
                strokeWidth: 0,
              );
            },
          ),
          belowBarData: BarAreaData(
            show: true,
            color: c.primary.withValues(alpha: 0.08),
          ),
        ),
      ],
    );
  }

  static String _fmt(double v) =>
      v == v.roundToDouble() ? v.toStringAsFixed(0) : v.toStringAsFixed(1);
}
