import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import '../hd/hd_models.dart' show AlertaItem;

/// Prescrição eletrônica geral com checagens em tempo real.
///
/// Monta a lista de itens localmente; ao salvar/assinar, a API devolve os
/// alertas (alergia, interação, dose máxima, ajuste renal) por item. Alertas
/// de bloqueio impedem a assinatura — o backend garante (409).
class PrescriptionScreen extends ConsumerStatefulWidget {
  final String pacienteId;
  const PrescriptionScreen({super.key, required this.pacienteId});

  @override
  ConsumerState<PrescriptionScreen> createState() => _PrescriptionScreenState();
}

class _ItemForm {
  String? medicamentoId;
  String? medicamentoNome;
  final dose = TextEditingController();
  final unidade = TextEditingController(text: 'mg');
  final via = TextEditingController(text: 'VO');
  final frequencia = TextEditingController();
  List<AlertaItem> alertas = [];

  void dispose() {
    dose.dispose();
    unidade.dispose();
    via.dispose();
    frequencia.dispose();
  }

  Map<String, dynamic> toJson() => {
        if (medicamentoId != null) 'medicamento_id': medicamentoId,
        if (double.tryParse(dose.text.replaceAll(',', '.')) != null)
          'dose': double.parse(dose.text.replaceAll(',', '.')),
        if (unidade.text.isNotEmpty) 'unidade_dose': unidade.text,
        if (via.text.isNotEmpty) 'via': via.text,
        if (frequencia.text.isNotEmpty) 'frequencia': frequencia.text,
      };
}

class _PrescriptionScreenState extends ConsumerState<PrescriptionScreen> {
  final List<_ItemForm> _itens = [_ItemForm()];
  List<Map<String, dynamic>> _catalogo = [];
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _carregarCatalogo();
  }

  @override
  void dispose() {
    for (final i in _itens) {
      i.dispose();
    }
    super.dispose();
  }

  Future<void> _carregarCatalogo() async {
    final r = await ref.read(apiClientProvider).dio.get('/api/v1/medicamentos');
    if (mounted) {
      setState(() => _catalogo = (r.data as List).cast<Map<String, dynamic>>());
    }
  }

  Future<void> _salvar({required bool assinar}) async {
    final itens =
        _itens.where((i) => i.medicamentoId != null).map((i) => i.toJson()).toList();
    if (itens.isEmpty) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final r = await ref.read(apiClientProvider).dio.post(
          '/api/v1/pacientes/${widget.pacienteId}/prescricoes',
          data: {'tipo': 'geral', 'itens': itens, 'assinar': assinar});
      final data = r.data as Map<String, dynamic>;
      // Reflete os alertas devolvidos pela API em cada item
      final retornados = (data['itens'] as List).cast<Map<String, dynamic>>();
      var idx = 0;
      for (final item in _itens) {
        if (item.medicamentoId == null) continue;
        item.alertas = ((retornados[idx]['alertas'] as List?) ?? const [])
            .map((a) => AlertaItem.fromJson(a as Map<String, dynamic>))
            .toList();
        idx++;
      }
      setState(() {});
      if (assinar && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Prescrição assinada — eMAR gerado automaticamente')));
        context.go('/pacientes/${widget.pacienteId}');
      }
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(
            onPressed: () => context.go('/pacientes/${widget.pacienteId}')),
        title: const Text('Prescrição geral'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(Gap.lg),
        children: [
          for (var i = 0; i < _itens.length; i++) ...[
            _ItemCard(
              item: _itens[i],
              catalogo: _catalogo,
              onRemover: _itens.length > 1
                  ? () => setState(() => _itens.removeAt(i).dispose())
                  : null,
              onChanged: () => setState(() {}),
            ),
            const SizedBox(height: Gap.md),
          ],
          OutlinedButton.icon(
            icon: const Icon(Icons.add),
            label: const Text('Adicionar medicamento'),
            onPressed: () => setState(() => _itens.add(_ItemForm())),
          ),
          if (_error != null) ...[
            const SizedBox(height: Gap.md),
            Text(_error!, style: TextStyle(color: c.critical)),
          ],
          const SizedBox(height: Gap.lg),
          Row(children: [
            Expanded(
              child: OutlinedButton(
                onPressed: _busy ? null : () => _salvar(assinar: false),
                child: const Text('Verificar / rascunho'),
              ),
            ),
            const SizedBox(width: Gap.md),
            Expanded(
              child: FilledButton(
                onPressed: _busy ? null : () => _salvar(assinar: true),
                child: _busy
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Assinar'),
              ),
            ),
          ]),
          const SizedBox(height: Gap.xxl),
        ],
      ),
    );
  }
}

class _ItemCard extends StatelessWidget {
  final _ItemForm item;
  final List<Map<String, dynamic>> catalogo;
  final VoidCallback? onRemover;
  final VoidCallback onChanged;
  const _ItemCard(
      {required this.item,
      required this.catalogo,
      this.onRemover,
      required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: item.medicamentoId,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Medicamento'),
                items: [
                  for (final m in catalogo)
                    DropdownMenuItem(
                      value: m['id'] as String,
                      child: Text(
                          '${m['principio_ativo']} — ${m['apresentacao']}',
                          overflow: TextOverflow.ellipsis),
                    ),
                ],
                onChanged: (v) {
                  item.medicamentoId = v;
                  onChanged();
                },
              ),
            ),
            if (onRemover != null)
              IconButton(
                  icon: const Icon(Icons.delete_outline),
                  onPressed: onRemover),
          ]),
          const SizedBox(height: Gap.md),
          Row(children: [
            Expanded(
                child: TextField(
                    controller: item.dose,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Dose'))),
            const SizedBox(width: Gap.md),
            Expanded(
                child: TextField(
                    controller: item.unidade,
                    decoration: const InputDecoration(labelText: 'Unidade'))),
            const SizedBox(width: Gap.md),
            Expanded(
                child: TextField(
                    controller: item.via,
                    decoration: const InputDecoration(labelText: 'Via'))),
          ]),
          const SizedBox(height: Gap.md),
          TextField(
              controller: item.frequencia,
              decoration: const InputDecoration(
                  labelText: 'Frequência (ex.: 8/8h, 2x/dia, se dor)',
                  helperText:
                      'Frequências reconhecidas geram o eMAR automaticamente')),
          if (item.alertas.isNotEmpty) ...[
            const SizedBox(height: Gap.md),
            for (final a in item.alertas)
              Padding(
                padding: const EdgeInsets.only(bottom: Gap.xs),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Icon(
                    a.gravidade == 'bloqueio'
                        ? Icons.block
                        : (a.gravidade == 'alerta'
                            ? Icons.warning_amber_rounded
                            : Icons.info_outline),
                    size: 16,
                    color: a.gravidade == 'bloqueio'
                        ? c.critical
                        : (a.gravidade == 'alerta' ? c.warn : c.info),
                  ),
                  const SizedBox(width: Gap.sm),
                  Expanded(
                      child: Text(a.mensagem,
                          style: Theme.of(context).textTheme.bodySmall)),
                ]),
              ),
          ],
        ],
      ),
    );
  }
}
