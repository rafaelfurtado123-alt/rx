import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import 'patient_repository.dart';

/// Cadastro do paciente renal — Ambulatório conservador ou Hemodiálise.
///
/// O segmento define os campos exigidos: HD pede início de TRS e turno;
/// o conservador entra direto na agenda do ambulatório.
class PatientFormScreen extends ConsumerStatefulWidget {
  const PatientFormScreen({super.key});

  @override
  ConsumerState<PatientFormScreen> createState() => _PatientFormScreenState();
}

class _PatientFormScreenState extends ConsumerState<PatientFormScreen> {
  final _form = GlobalKey<FormState>();
  final _nome = TextEditingController();
  final _cns = TextEditingController();
  final _cpf = TextEditingController();
  final _etiologia = TextEditingController();
  String? _sexo;
  DateTime? _nascimento;
  int? _estagio;
  String _segmento = 'conservador';
  DateTime? _inicioTrs;
  String? _turno;
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    for (final c in [_nome, _cns, _cpf, _etiologia]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _salvar() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final header = await ref.read(patientRepositoryProvider).criar({
        'nome': _nome.text.trim(),
        if (_cns.text.isNotEmpty) 'cns': _cns.text.trim(),
        if (_cpf.text.isNotEmpty) 'cpf': _cpf.text.trim(),
        if (_sexo != null) 'sexo': _sexo,
        if (_nascimento != null)
          'data_nascimento': DateFormat('yyyy-MM-dd').format(_nascimento!),
        if (_etiologia.text.isNotEmpty) 'etiologia_drc': _etiologia.text,
        if (_estagio != null) 'estagio_drc': _estagio,
        'segmento': _segmento,
        if (_inicioTrs != null)
          'inicio_trs': DateFormat('yyyy-MM-dd').format(_inicioTrs!),
        if (_turno != null) 'turno_dialise': _turno,
      });
      ref.invalidate(pacientesProvider);
      if (mounted) context.go('/pacientes/${header.id}');
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _escolherData(bool nascimento) async {
    final hoje = DateTime.now();
    final data = await showDatePicker(
      context: context,
      firstDate: DateTime(1900),
      lastDate: hoje,
      initialDate: nascimento ? DateTime(1960) : hoje,
    );
    if (data != null) {
      setState(() => nascimento ? _nascimento = data : _inicioTrs = data);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final ehHd = _segmento == 'hemodialise';

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(onPressed: () => context.go('/pacientes')),
        title: const Text('Novo paciente renal'),
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
                  Text('Segmento de cuidado',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: Gap.md),
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(
                          value: 'conservador',
                          icon: Icon(Icons.event_note_outlined),
                          label: Text('Ambulatório conservador')),
                      ButtonSegment(
                          value: 'hemodialise',
                          icon: Icon(Icons.water_drop_outlined),
                          label: Text('Hemodiálise')),
                    ],
                    selected: {_segmento},
                    onSelectionChanged: (s) =>
                        setState(() => _segmento = s.first),
                  ),
                ],
              ),
            ),
            const SizedBox(height: Gap.md),
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Identificação',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: Gap.md),
                  TextFormField(
                    controller: _nome,
                    decoration:
                        const InputDecoration(labelText: 'Nome completo *'),
                    validator: (v) => (v == null || v.trim().length < 3)
                        ? 'Informe o nome'
                        : null,
                  ),
                  const SizedBox(height: Gap.md),
                  Row(children: [
                    Expanded(
                      child: TextFormField(
                        controller: _cns,
                        maxLength: 15,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                            labelText: 'CNS (Cartão SUS)', counterText: ''),
                      ),
                    ),
                    const SizedBox(width: Gap.md),
                    Expanded(
                      child: TextFormField(
                        controller: _cpf,
                        maxLength: 11,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                            labelText: 'CPF', counterText: ''),
                      ),
                    ),
                  ]),
                  const SizedBox(height: Gap.md),
                  Row(children: [
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        initialValue: _sexo,
                        decoration: const InputDecoration(labelText: 'Sexo'),
                        items: const [
                          DropdownMenuItem(
                              value: 'masculino', child: Text('Masculino')),
                          DropdownMenuItem(
                              value: 'feminino', child: Text('Feminino')),
                          DropdownMenuItem(
                              value: 'intersexo', child: Text('Intersexo')),
                          DropdownMenuItem(
                              value: 'nao_informado',
                              child: Text('Não informado')),
                        ],
                        onChanged: (v) => setState(() => _sexo = v),
                      ),
                    ),
                    const SizedBox(width: Gap.md),
                    Expanded(
                      child: OutlinedButton.icon(
                        icon: const Icon(Icons.cake_outlined, size: 16),
                        onPressed: () => _escolherData(true),
                        label: Text(_nascimento == null
                            ? 'Nascimento'
                            : DateFormat('dd/MM/yyyy').format(_nascimento!)),
                      ),
                    ),
                  ]),
                ],
              ),
            ),
            const SizedBox(height: Gap.md),
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Doença renal',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: Gap.md),
                  TextFormField(
                    controller: _etiologia,
                    decoration: const InputDecoration(
                        labelText:
                            'Etiologia da DRC (ex.: nefropatia diabética)'),
                  ),
                  const SizedBox(height: Gap.md),
                  DropdownButtonFormField<int>(
                    initialValue: _estagio,
                    decoration:
                        const InputDecoration(labelText: 'Estágio da DRC'),
                    items: [
                      for (var e = 1; e <= 5; e++)
                        DropdownMenuItem(value: e, child: Text('Estágio $e')),
                    ],
                    onChanged: (v) => setState(() => _estagio = v),
                  ),
                  if (ehHd) ...[
                    const SizedBox(height: Gap.md),
                    Row(children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          icon: const Icon(Icons.event, size: 16),
                          onPressed: () => _escolherData(false),
                          label: Text(_inicioTrs == null
                              ? 'Início da TRS *'
                              : DateFormat('dd/MM/yyyy').format(_inicioTrs!)),
                        ),
                      ),
                      const SizedBox(width: Gap.md),
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          initialValue: _turno,
                          decoration:
                              const InputDecoration(labelText: 'Turno'),
                          items: const [
                            DropdownMenuItem(
                                value: 'manha', child: Text('Manhã')),
                            DropdownMenuItem(
                                value: 'tarde', child: Text('Tarde')),
                            DropdownMenuItem(
                                value: 'noite', child: Text('Noite')),
                          ],
                          onChanged: (v) => setState(() => _turno = v),
                        ),
                      ),
                    ]),
                  ],
                ],
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: Gap.md),
              Text(_error!, style: TextStyle(color: c.critical)),
            ],
            const SizedBox(height: Gap.lg),
            FilledButton(
              onPressed: _saving ? null : _salvar,
              child: _saving
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Cadastrar paciente'),
            ),
            const SizedBox(height: Gap.xxl),
          ],
        ),
      ),
    );
  }
}
