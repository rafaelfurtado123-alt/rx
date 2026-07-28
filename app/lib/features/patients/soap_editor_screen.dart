import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import 'patient_repository.dart';

/// Editor de evolução SOAP com sumarização por IA e assinatura.
class SoapEditorScreen extends ConsumerStatefulWidget {
  final String pacienteId;
  const SoapEditorScreen({super.key, required this.pacienteId});

  @override
  ConsumerState<SoapEditorScreen> createState() => _SoapEditorScreenState();
}

class _SoapEditorScreenState extends ConsumerState<SoapEditorScreen> {
  final _s = TextEditingController();
  final _o = TextEditingController();
  final _a = TextEditingController();
  final _p = TextEditingController();
  final _livre = TextEditingController();
  String _categoria = 'medica';
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    for (final ctl in [_s, _o, _a, _p, _livre]) {
      ctl.dispose();
    }
    super.dispose();
  }

  Map<String, dynamic> _soap({bool assinar = false}) => {
        'categoria': _categoria,
        if (_s.text.isNotEmpty) 'subjetivo': _s.text,
        if (_o.text.isNotEmpty) 'objetivo': _o.text,
        if (_a.text.isNotEmpty) 'avaliacao': _a.text,
        if (_p.text.isNotEmpty) 'plano': _p.text,
        if (_livre.text.isNotEmpty) 'texto_livre': _livre.text,
        'assinar': assinar,
      };

  Future<void> _sumarizar() async {
    final resumo = await ref
        .read(patientRepositoryProvider)
        .resumoIa(widget.pacienteId, _soap());
    if (mounted) setState(() => _livre.text = resumo);
    _snack('Rascunho gerado pela IA — revise antes de assinar.');
  }

  Future<void> _salvar({required bool assinar}) async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ref
          .read(patientRepositoryProvider)
          .criarEvolucao(widget.pacienteId, _soap(assinar: assinar));
      ref.invalidate(evolucoesProvider(widget.pacienteId));
      ref.invalidate(timelineProvider(widget.pacienteId));
      if (mounted) context.go('/pacientes/${widget.pacienteId}');
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _snack(String msg) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(msg)));

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(
            onPressed: () => context.go('/pacientes/${widget.pacienteId}')),
        title: const Text('Nova evolução'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(Gap.lg),
        children: [
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: _categoria,
                  decoration: const InputDecoration(labelText: 'Categoria'),
                  items: const [
                    DropdownMenuItem(value: 'medica', child: Text('Médica')),
                    DropdownMenuItem(value: 'enfermagem', child: Text('Enfermagem')),
                    DropdownMenuItem(value: 'nutricao', child: Text('Nutrição')),
                  ],
                  onChanged: (v) => setState(() => _categoria = v ?? 'medica'),
                ),
                const SizedBox(height: Gap.md),
                _campo(_s, 'S — Subjetivo'),
                _campo(_o, 'O — Objetivo'),
                _campo(_a, 'A — Avaliação'),
                _campo(_p, 'P — Plano'),
              ],
            ),
          ),
          const SizedBox(height: Gap.md),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text('Texto / Resumo',
                          style: Theme.of(context).textTheme.titleMedium),
                    ),
                    TextButton.icon(
                      icon: const Icon(Icons.auto_awesome, size: 16),
                      label: const Text('Sumarizar com IA'),
                      onPressed: _sumarizar,
                    ),
                  ],
                ),
                _campo(_livre, 'Texto livre', maxLines: 5),
              ],
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: Gap.md),
            Text(_error!, style: TextStyle(color: c.critical)),
          ],
          const SizedBox(height: Gap.lg),
          Row(
            children: [
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
                      : const Text('Assinar e fechar'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _campo(TextEditingController ctl, String label, {int maxLines = 2}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: Gap.md),
      child: TextField(
        controller: ctl,
        maxLines: maxLines,
        decoration: InputDecoration(labelText: label),
      ),
    );
  }
}
