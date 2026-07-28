import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/providers.dart';
import '../../theme/theme.dart';
import '../../widgets/widgets.dart';

/// eMAR — checagem eletrônica de administração (visão da enfermagem).
///
/// Lista as doses previstas do paciente; cada dose é registrada como
/// administrada/recusada/omitida com lote e observação. Registros fechados
/// são imutáveis (o backend garante).
class EmarScreen extends ConsumerStatefulWidget {
  final String pacienteId;
  const EmarScreen({super.key, required this.pacienteId});

  @override
  ConsumerState<EmarScreen> createState() => _EmarScreenState();
}

final _emarPendentesProvider =
    FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>(
        (ref, pacienteId) async {
  final r = await ref.watch(apiClientProvider).dio.get(
      '/api/v1/pacientes/$pacienteId/emar',
      queryParameters: {'pendentes': true});
  return (r.data as List).cast<Map<String, dynamic>>();
});

class _EmarScreenState extends ConsumerState<EmarScreen> {
  bool _busy = false;

  Future<void> _registrar(String emarId, String status,
      {String? lote, String? observacao}) async {
    setState(() => _busy = true);
    try {
      await ref.read(apiClientProvider).dio.post(
          '/api/v1/emar/$emarId/registrar',
          data: {
            'status': status,
            if (lote != null && lote.isNotEmpty) 'lote': lote,
            if (observacao != null && observacao.isNotEmpty)
              'observacao': observacao,
          });
      ref.invalidate(_emarPendentesProvider(widget.pacienteId));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final doses = ref.watch(_emarPendentesProvider(widget.pacienteId));

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(
            onPressed: () => context.go('/pacientes/${widget.pacienteId}')),
        title: const Text('eMAR — administração'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () =>
                ref.invalidate(_emarPendentesProvider(widget.pacienteId)),
          ),
        ],
      ),
      body: doses.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (lista) => lista.isEmpty
            ? Center(
                child: Text('Nenhuma dose pendente',
                    style: TextStyle(color: c.textSecondary)))
            : ListView.separated(
                padding: const EdgeInsets.all(Gap.lg),
                itemCount: lista.length,
                separatorBuilder: (_, __) => const SizedBox(height: Gap.sm),
                itemBuilder: (context, i) {
                  final d = lista[i];
                  final horario = DateTime.parse(d['horario_previsto'] as String)
                      .toLocal();
                  final atrasada = horario.isBefore(DateTime.now());
                  final doseTxt = [
                    if (d['dose'] != null)
                      '${d['dose']} ${d['unidade_dose'] ?? ''}'.trim(),
                    if (d['via'] != null) d['via'],
                  ].join(' · ');
                  return GlassCard(
                    onTap: _busy ? null : () => _abrirRegistro(d),
                    child: Row(children: [
                      Column(children: [
                        Text(DateFormat('HH:mm').format(horario),
                            style: NefronType.mono(
                                color: atrasada ? c.critical : c.primary,
                                size: 18)),
                        Text(DateFormat('dd/MM').format(horario),
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(color: c.textSecondary)),
                      ]),
                      const SizedBox(width: Gap.lg),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(d['medicamento'] as String? ?? '—',
                                style:
                                    Theme.of(context).textTheme.titleMedium),
                            if (doseTxt.isNotEmpty)
                              Text(doseTxt,
                                  style: Theme.of(context)
                                      .textTheme
                                      .bodySmall
                                      ?.copyWith(color: c.textSecondary)),
                          ],
                        ),
                      ),
                      if (atrasada)
                        StatusPill(label: 'Atrasada', status: 'critical')
                      else
                        StatusPill(label: 'Prevista', status: 'info'),
                    ]),
                  );
                },
              ),
      ),
    );
  }

  Future<void> _abrirRegistro(Map<String, dynamic> dose) async {
    final lote = TextEditingController();
    final obs = TextEditingController();
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
            left: Gap.lg,
            right: Gap.lg,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + Gap.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${dose['medicamento'] ?? 'Dose'}',
                style: Theme.of(ctx).textTheme.titleMedium),
            const SizedBox(height: Gap.md),
            TextField(
                controller: lote,
                decoration: const InputDecoration(labelText: 'Lote')),
            const SizedBox(height: Gap.md),
            TextField(
                controller: obs,
                decoration: const InputDecoration(labelText: 'Observação')),
            const SizedBox(height: Gap.lg),
            Row(children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () {
                    Navigator.pop(ctx);
                    _registrar(dose['id'] as String, 'recusado',
                        observacao: obs.text);
                  },
                  child: const Text('Recusada'),
                ),
              ),
              const SizedBox(width: Gap.md),
              Expanded(
                child: FilledButton(
                  onPressed: () {
                    Navigator.pop(ctx);
                    _registrar(dose['id'] as String, 'administrado',
                        lote: lote.text, observacao: obs.text);
                  },
                  child: const Text('Administrada ✓'),
                ),
              ),
            ]),
            const SizedBox(height: Gap.md),
          ],
        ),
      ),
    );
    lote.dispose();
    obs.dispose();
  }
}
