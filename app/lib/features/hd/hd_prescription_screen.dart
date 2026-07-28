import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import 'hd_models.dart';
import 'hd_repository.dart';

/// Prescrição de Hemodiálise — formulário completo nível Tasy.
///
/// O volume a ultrafiltrar é recalculado ao vivo (peso atual − peso seco),
/// espelhando a coluna gerada no banco.
class HdPrescriptionScreen extends ConsumerStatefulWidget {
  final String pacienteId;
  const HdPrescriptionScreen({super.key, required this.pacienteId});

  @override
  ConsumerState<HdPrescriptionScreen> createState() =>
      _HdPrescriptionScreenState();
}

class _HdPrescriptionScreenState extends ConsumerState<HdPrescriptionScreen> {
  final _form = GlobalKey<FormState>();
  String _modalidade = 'IHD';
  final _duracao = TextEditingController(text: '240');
  final _qb = TextEditingController(text: '350');
  final _qd = TextEditingController(text: '500');
  final _dialisador = TextEditingController();
  String? _acessoId;
  final _pontoPuncao = TextEditingController();
  final _pesoAtual = TextEditingController();
  final _pesoSeco = TextEditingController();
  final _ufPrescrita = TextEditingController();
  final _ufMaxima = TextEditingController();
  final _sodioIni = TextEditingController(text: '145');
  final _sodioFim = TextEditingController(text: '138');
  final _bicarbonato = TextEditingController(text: '32');
  final _heparinaBolus = TextEditingController();
  final _heparinaManutencao = TextEditingController();
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    for (final c in [
      _duracao, _qb, _qd, _dialisador, _pontoPuncao, _pesoAtual, _pesoSeco,
      _ufPrescrita, _ufMaxima, _sodioIni, _sodioFim, _bicarbonato,
      _heparinaBolus, _heparinaManutencao,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  double? get _volumeCalculado {
    final atual = double.tryParse(_pesoAtual.text.replaceAll(',', '.'));
    final seco = double.tryParse(_pesoSeco.text.replaceAll(',', '.'));
    if (atual == null || seco == null) return null;
    final v = atual - seco;
    return v > 0 ? double.parse(v.toStringAsFixed(2)) : 0;
  }

  double? _num(TextEditingController c) =>
      double.tryParse(c.text.replaceAll(',', '.'));
  int? _int(TextEditingController c) => int.tryParse(c.text);

  Map<String, dynamic> _payload({required bool assinar}) => {
        'modalidade': _modalidade,
        'duracao_min': _int(_duracao) ?? 240,
        if (_int(_qb) != null) 'qb_ml_min': _int(_qb),
        if (_int(_qd) != null) 'qd_ml_min': _int(_qd),
        if (_dialisador.text.isNotEmpty) 'dialisador_modelo': _dialisador.text,
        if (_acessoId != null) 'acesso_id': _acessoId,
        if (_pontoPuncao.text.isNotEmpty) 'ponto_puncao': _pontoPuncao.text,
        if (_num(_pesoAtual) != null) 'peso_atual_kg': _num(_pesoAtual),
        if (_num(_pesoSeco) != null) 'peso_seco_kg': _num(_pesoSeco),
        if (_num(_ufPrescrita) != null) 'uf_prescrita_l': _num(_ufPrescrita),
        if (_num(_ufMaxima) != null) 'uf_maxima_l': _num(_ufMaxima),
        'perfil_sodio': {
          'tipo': 'ramp',
          'ini': _num(_sodioIni),
          'fim': _num(_sodioFim),
        },
        'perfil_bicarbonato': {'valor': _num(_bicarbonato)},
        if (_num(_heparinaBolus) != null || _num(_heparinaManutencao) != null)
          'heparinizacao': {
            'tipo': 'sistemica',
            if (_num(_heparinaBolus) != null) 'bolus_ui': _num(_heparinaBolus),
            if (_num(_heparinaManutencao) != null)
              'manutencao_ui_h': _num(_heparinaManutencao),
          },
        'assinar': assinar,
      };

  Future<void> _salvar({required bool assinar}) async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final presc = await ref
          .read(hdRepositoryProvider)
          .criarPrescricaoHd(widget.pacienteId, _payload(assinar: assinar));
      ref.invalidate(prescricoesHdProvider(widget.pacienteId));
      if (!mounted) return;
      if (presc.alertas.isNotEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(presc.alertas.map((a) => a.mensagem).join(' · '))));
      }
      context.go('/pacientes/${widget.pacienteId}');
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final acessos = ref.watch(acessosProvider(widget.pacienteId));
    final volume = _volumeCalculado;

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(
            onPressed: () => context.go('/pacientes/${widget.pacienteId}')),
        title: const Text('Prescrição de HD'),
      ),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(Gap.lg),
          children: [
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Modalidade e tempo',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: Gap.md),
                  DropdownButtonFormField<String>(
                    initialValue: _modalidade,
                    decoration: const InputDecoration(labelText: 'Modalidade'),
                    items: const [
                      DropdownMenuItem(value: 'IHD', child: Text('IHD')),
                      DropdownMenuItem(value: 'SLED', child: Text('SLED')),
                      DropdownMenuItem(
                          value: 'HDF_online', child: Text('HDF online')),
                      DropdownMenuItem(value: 'CVVHD', child: Text('CVVHD')),
                      DropdownMenuItem(value: 'CVVHDF', child: Text('CVVHDF')),
                    ],
                    onChanged: (v) => setState(() => _modalidade = v ?? 'IHD'),
                  ),
                  const SizedBox(height: Gap.md),
                  Row(children: [
                    Expanded(
                        child: _campoNum(_duracao, 'Duração (min)',
                            obrigatorio: true)),
                    const SizedBox(width: Gap.md),
                    Expanded(child: _campoNum(_qb, 'Qb (mL/min)')),
                    const SizedBox(width: Gap.md),
                    Expanded(child: _campoNum(_qd, 'Qd (mL/min)')),
                  ]),
                ],
              ),
            ),
            const SizedBox(height: Gap.md),
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Dialisador e acesso',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: Gap.md),
                  _campoTexto(_dialisador, 'Modelo do dialisador (ex.: FX80)'),
                  const SizedBox(height: Gap.md),
                  acessos.maybeWhen(
                    data: (lista) => DropdownButtonFormField<String>(
                      initialValue: _acessoId,
                      decoration:
                          const InputDecoration(labelText: 'Acesso vascular'),
                      items: [
                        for (final a in lista)
                          DropdownMenuItem(value: a.id, child: Text(a.rotulo)),
                      ],
                      onChanged: (v) => setState(() => _acessoId = v),
                    ),
                    orElse: () => const LinearProgressIndicator(),
                  ),
                  const SizedBox(height: Gap.md),
                  _campoTexto(_pontoPuncao, 'Ponto de punção'),
                ],
              ),
            ),
            const SizedBox(height: Gap.md),
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Peso e ultrafiltração',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: Gap.md),
                  Row(children: [
                    Expanded(
                        child: _campoNum(_pesoAtual, 'Peso atual (kg)',
                            aoMudar: () => setState(() {}))),
                    const SizedBox(width: Gap.md),
                    Expanded(
                        child: _campoNum(_pesoSeco, 'Peso seco (kg)',
                            aoMudar: () => setState(() {}))),
                  ]),
                  const SizedBox(height: Gap.md),
                  Row(children: [
                    Expanded(child: _campoNum(_ufPrescrita, 'UF prescrita (L)')),
                    const SizedBox(width: Gap.md),
                    Expanded(child: _campoNum(_ufMaxima, 'UF máxima (L)')),
                  ]),
                  if (volume != null) ...[
                    const SizedBox(height: Gap.md),
                    Row(children: [
                      Icon(Icons.calculate_outlined,
                          size: 18, color: c.primary),
                      const SizedBox(width: Gap.sm),
                      Text('Volume calculado: ',
                          style: Theme.of(context).textTheme.bodyMedium),
                      Text('$volume L',
                          style: NefronType.mono(color: c.primary, size: 16)),
                    ]),
                  ],
                ],
              ),
            ),
            const SizedBox(height: Gap.md),
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Perfis e heparinização',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: Gap.md),
                  Row(children: [
                    Expanded(child: _campoNum(_sodioIni, 'Na inicial')),
                    const SizedBox(width: Gap.md),
                    Expanded(child: _campoNum(_sodioFim, 'Na final')),
                    const SizedBox(width: Gap.md),
                    Expanded(child: _campoNum(_bicarbonato, 'Bicarbonato')),
                  ]),
                  const SizedBox(height: Gap.md),
                  Row(children: [
                    Expanded(
                        child: _campoNum(_heparinaBolus, 'Heparina bolus (UI)')),
                    const SizedBox(width: Gap.md),
                    Expanded(
                        child: _campoNum(
                            _heparinaManutencao, 'Manutenção (UI/h)')),
                  ]),
                ],
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: Gap.md),
              Text(_error!, style: TextStyle(color: c.critical)),
            ],
            const SizedBox(height: Gap.lg),
            Row(children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _saving ? null : () => _salvar(assinar: false),
                  child: const Text('Salvar rascunho'),
                ),
              ),
              const SizedBox(width: Gap.md),
              Expanded(
                child: FilledButton(
                  onPressed: _saving ? null : () => _salvar(assinar: true),
                  child: _saving
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Assinar prescrição'),
                ),
              ),
            ]),
            const SizedBox(height: Gap.xxl),
          ],
        ),
      ),
    );
  }

  Widget _campoNum(TextEditingController ctl, String label,
      {bool obrigatorio = false, VoidCallback? aoMudar}) {
    return TextFormField(
      controller: ctl,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration: InputDecoration(labelText: label),
      onChanged: aoMudar == null ? null : (_) => aoMudar(),
      validator: obrigatorio
          ? (v) => (v == null || v.isEmpty) ? 'Obrigatório' : null
          : null,
    );
  }

  Widget _campoTexto(TextEditingController ctl, String label) {
    return TextFormField(
        controller: ctl, decoration: InputDecoration(labelText: label));
  }
}
