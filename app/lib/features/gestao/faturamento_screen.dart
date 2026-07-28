import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/providers.dart';
import '../../theme/theme.dart';
import '../../widgets/widgets.dart';

/// Faturamento SUS: geração da produção da competência + contas + APAC.
class FaturamentoScreen extends ConsumerStatefulWidget {
  const FaturamentoScreen({super.key});

  @override
  ConsumerState<FaturamentoScreen> createState() => _FaturamentoScreenState();
}

final _contasProvider = FutureProvider.autoDispose
    .family<List<Map<String, dynamic>>, String>((ref, competencia) async {
  final r = await ref.watch(apiClientProvider).dio.get('/api/v1/fatura/contas',
      queryParameters: {'competencia': competencia});
  return (r.data as List).cast<Map<String, dynamic>>();
});

class _FaturamentoScreenState extends ConsumerState<FaturamentoScreen> {
  DateTime _competencia = DateTime.now();
  bool _busy = false;

  String get _comp => DateFormat('yyyy-MM').format(_competencia);

  Future<void> _gerarProducao() async {
    setState(() => _busy = true);
    try {
      final r = await ref.read(apiClientProvider).dio.post(
          '/api/v1/fatura/producao',
          queryParameters: {'competencia': _comp});
      final d = r.data as Map<String, dynamic>;
      ref.invalidate(_contasProvider(_comp));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('${d['contas_criadas']} conta(s) criada(s) · '
                '${d['sessoes_faturadas']} sessão(ões) faturada(s) · '
                '${d['contas_existentes']} já existente(s)')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _mudarMes(int delta) {
    setState(() => _competencia =
        DateTime(_competencia.year, _competencia.month + delta, 1));
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final contas = ref.watch(_contasProvider(_comp));

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(onPressed: () => context.go('/dashboard')),
        title: const Text('Faturamento SUS'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(Gap.lg),
        children: [
          GlassCard(
            child: Row(children: [
              IconButton(
                  icon: const Icon(Icons.chevron_left),
                  onPressed: () => _mudarMes(-1)),
              Expanded(
                child: Center(
                  child: Text(
                    DateFormat("MMMM 'de' yyyy", 'pt_BR').format(_competencia),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ),
              IconButton(
                  icon: const Icon(Icons.chevron_right),
                  onPressed: () => _mudarMes(1)),
            ]),
          ),
          const SizedBox(height: Gap.md),
          Row(children: [
            Expanded(
              child: FilledButton.icon(
                icon: const Icon(Icons.play_arrow),
                onPressed: _busy ? null : _gerarProducao,
                label: const Text('Gerar produção do mês'),
              ),
            ),
          ]),
          const SizedBox(height: Gap.sm),
          Text(
            'Gera as contas (APAC de hemodiálise) a partir das sessões '
            'encerradas na competência. Idempotente: reexecutar não duplica. '
            'O CSV de conferência está em /fatura/contas/export.',
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(color: c.textSecondary),
          ),
          const SizedBox(height: Gap.xl),
          Text('Contas da competência',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.md),
          contas.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Text('$e'),
            data: (lista) => lista.isEmpty
                ? Text('Nenhuma conta gerada nesta competência',
                    style: TextStyle(color: c.textSecondary))
                : Column(children: [
                    for (final conta in lista) ...[
                      _ContaCard(conta: conta),
                      const SizedBox(height: Gap.sm),
                    ],
                  ]),
          ),
        ],
      ),
    );
  }
}

class _ContaCard extends StatelessWidget {
  final Map<String, dynamic> conta;
  const _ContaCard({required this.conta});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final itens = (conta['itens'] as List).cast<Map<String, dynamic>>();
    return GlassCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(conta['paciente_nome'] as String? ?? '—',
                      style: Theme.of(context).textTheme.titleMedium),
                  if (conta['paciente_cns'] != null)
                    Text('CNS ${conta['paciente_cns']}',
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: c.textSecondary)),
                ]),
          ),
          StatusPill(
              label: conta['status'] as String,
              status:
                  conta['status'] == 'aberta' ? 'warn' : 'ok'),
        ]),
        const SizedBox(height: Gap.sm),
        for (final item in itens)
          Row(children: [
            Expanded(
              child: Text(
                '${item['sigtap_codigo']} — ${item['descricao'] ?? ''}',
                style: Theme.of(context).textTheme.bodySmall,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            Text('×${item['quantidade']}',
                style: NefronType.mono(color: c.primary, size: 14)),
          ]),
      ]),
    );
  }
}
