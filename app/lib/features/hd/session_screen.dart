import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import 'hd_models.dart';
import 'hd_repository.dart';

/// Módulo de Sessão de HD (beira-leito): recepção → em sessão → encerramento.
///
/// A etapa exibida segue o estado da sessão mais recente do paciente; ao
/// encerrar, mostra Kt/V, URR e nPCR calculados automaticamente.
class SessionScreen extends ConsumerStatefulWidget {
  final String pacienteId;
  const SessionScreen({super.key, required this.pacienteId});

  @override
  ConsumerState<SessionScreen> createState() => _SessionScreenState();
}

class _SessionScreenState extends ConsumerState<SessionScreen> {
  bool _busy = false;
  String? _error;

  Future<T?> _run<T>(Future<T> Function() op) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final r = await op();
      ref.invalidate(sessoesProvider(widget.pacienteId));
      return r;
    } catch (e) {
      setState(() => _error = '$e');
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final sessoes = ref.watch(sessoesProvider(widget.pacienteId));

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(
            onPressed: () => context.go('/pacientes/${widget.pacienteId}')),
        title: const Text('Sessão de HD'),
      ),
      body: sessoes.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (lista) {
          final atual = lista.isEmpty ? null : lista.first;
          return ListView(
            padding: const EdgeInsets.all(Gap.lg),
            children: [
              if (_error != null) ...[
                GlassCard(
                    child:
                        Text(_error!, style: TextStyle(color: c.critical))),
                const SizedBox(height: Gap.md),
              ],
              if (atual == null || atual.encerrada)
                _RecepcaoCard(
                    busy: _busy,
                    onSubmit: (body) => _run(() => ref
                        .read(hdRepositoryProvider)
                        .recepcao(widget.pacienteId, body))),
              if (atual != null && !atual.encerrada && atual.inicio == null)
                _AguardandoInicioCard(
                    sessao: atual,
                    busy: _busy,
                    onIniciar: (maquina) => _run(() => ref
                        .read(hdRepositoryProvider)
                        .iniciar(atual.id, maquina: maquina))),
              if (atual != null && atual.emAndamento)
                _EmSessaoCard(
                  sessao: atual,
                  busy: _busy,
                  onParametro: (body) => _run(() => ref
                      .read(hdRepositoryProvider)
                      .registrarParametro(atual.id, body)),
                  onIntercorrencia: (body) => _run(() => ref
                      .read(hdRepositoryProvider)
                      .registrarIntercorrencia(atual.id, body)),
                  onEncerrar: (body) => _run(() =>
                      ref.read(hdRepositoryProvider).encerrar(atual.id, body)),
                ),
              if (atual != null && atual.encerrada) ...[
                const SizedBox(height: Gap.md),
                _ResultadoCard(sessao: atual),
              ],
            ],
          );
        },
      ),
    );
  }
}

// ------------------------- Recepção -------------------------
class _RecepcaoCard extends StatefulWidget {
  final bool busy;
  final Future<void> Function(Map<String, dynamic>) onSubmit;
  const _RecepcaoCard({required this.busy, required this.onSubmit});

  @override
  State<_RecepcaoCard> createState() => _RecepcaoCardState();
}

class _RecepcaoCardState extends State<_RecepcaoCard> {
  final _peso = TextEditingController();
  final _pa = TextEditingController();
  final _fc = TextEditingController();
  final _temp = TextEditingController();
  final _queixas = TextEditingController();

  @override
  void dispose() {
    for (final c in [_peso, _pa, _fc, _temp, _queixas]) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Recepção do paciente',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.md),
          Row(children: [
            Expanded(child: _num(_peso, 'Peso pré (kg)')),
            const SizedBox(width: Gap.md),
            Expanded(child: _txt(_pa, 'PA (ex.: 140/85)')),
          ]),
          const SizedBox(height: Gap.md),
          Row(children: [
            Expanded(child: _num(_fc, 'FC (bpm)')),
            const SizedBox(width: Gap.md),
            Expanded(child: _num(_temp, 'Temperatura (°C)')),
          ]),
          const SizedBox(height: Gap.md),
          _txt(_queixas, 'Queixas'),
          const SizedBox(height: Gap.lg),
          FilledButton(
            onPressed: widget.busy
                ? null
                : () {
                    final peso =
                        double.tryParse(_peso.text.replaceAll(',', '.'));
                    if (peso == null) return;
                    widget.onSubmit({
                      'peso_pre_kg': peso,
                      if (_pa.text.isNotEmpty) 'pa_pre': _pa.text,
                      if (int.tryParse(_fc.text) != null)
                        'fc_pre': int.parse(_fc.text),
                      if (double.tryParse(
                              _temp.text.replaceAll(',', '.')) !=
                          null)
                        'temp_pre':
                            double.parse(_temp.text.replaceAll(',', '.')),
                      if (_queixas.text.isNotEmpty) 'queixas': _queixas.text,
                    });
                  },
            child: const Text('Registrar recepção'),
          ),
        ],
      ),
    );
  }
}

// ------------------------- Aguardando início -------------------------
class _AguardandoInicioCard extends StatefulWidget {
  final SessaoHD sessao;
  final bool busy;
  final Future<void> Function(String?) onIniciar;
  const _AguardandoInicioCard(
      {required this.sessao, required this.busy, required this.onIniciar});

  @override
  State<_AguardandoInicioCard> createState() => _AguardandoInicioCardState();
}

class _AguardandoInicioCardState extends State<_AguardandoInicioCard> {
  final _maquina = TextEditingController();

  @override
  void dispose() {
    _maquina.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Recepção registrada',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.sm),
          Wrap(spacing: Gap.sm, runSpacing: Gap.sm, children: [
            if (widget.sessao.pesoPreKg != null)
              StatusPill(
                  label: 'Peso ${widget.sessao.pesoPreKg} kg', status: 'info'),
            if (widget.sessao.paPre != null)
              StatusPill(label: 'PA ${widget.sessao.paPre}', status: 'info'),
            for (final a in widget.sessao.alertas)
              StatusPill(label: a.mensagem, status: 'warn'),
          ]),
          const SizedBox(height: Gap.lg),
          TextField(
              controller: _maquina,
              decoration:
                  const InputDecoration(labelText: 'Máquina (ex.: M03)')),
          const SizedBox(height: Gap.lg),
          FilledButton.icon(
            icon: Icon(Icons.play_arrow, color: c.onBrand),
            onPressed: widget.busy
                ? null
                : () => widget.onIniciar(
                    _maquina.text.isEmpty ? null : _maquina.text),
            label: const Text('Iniciar sessão'),
          ),
        ],
      ),
    );
  }
}

// ------------------------- Em sessão -------------------------
class _EmSessaoCard extends StatefulWidget {
  final SessaoHD sessao;
  final bool busy;
  final Future<void> Function(Map<String, dynamic>) onParametro;
  final Future<void> Function(Map<String, dynamic>) onIntercorrencia;
  final Future<void> Function(Map<String, dynamic>) onEncerrar;
  const _EmSessaoCard({
    required this.sessao,
    required this.busy,
    required this.onParametro,
    required this.onIntercorrencia,
    required this.onEncerrar,
  });

  @override
  State<_EmSessaoCard> createState() => _EmSessaoCardState();
}

class _EmSessaoCardState extends State<_EmSessaoCard> {
  final _pa = TextEditingController();
  final _fc = TextEditingController();
  final _pesoPos = TextEditingController();
  final _ureiaPre = TextEditingController();
  final _ureiaPos = TextEditingController();

  @override
  void dispose() {
    for (final c in [_pa, _fc, _pesoPos, _ureiaPre, _ureiaPos]) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Column(children: [
      GlassCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.monitor_heart_outlined, color: c.primary),
              const SizedBox(width: Gap.sm),
              Text('Em sessão', style: Theme.of(context).textTheme.titleMedium),
              const Spacer(),
              if (widget.sessao.maquina != null)
                StatusPill(
                    label: widget.sessao.maquina!, status: 'info'),
            ]),
            const SizedBox(height: Gap.md),
            Row(children: [
              Expanded(child: _txt(_pa, 'PA')),
              const SizedBox(width: Gap.md),
              Expanded(child: _num(_fc, 'FC')),
              const SizedBox(width: Gap.md),
              FilledButton.tonal(
                onPressed: widget.busy
                    ? null
                    : () => widget.onParametro({
                          if (_pa.text.isNotEmpty) 'pa': _pa.text,
                          if (int.tryParse(_fc.text) != null)
                            'fc': int.parse(_fc.text),
                        }),
                child: const Text('Registrar'),
              ),
            ]),
            const SizedBox(height: Gap.sm),
            TextButton.icon(
              icon: const Icon(Icons.report_problem_outlined, size: 16),
              label: const Text('+ Intercorrência'),
              onPressed: widget.busy ? null : () => _dialogIntercorrencia(),
            ),
          ],
        ),
      ),
      const SizedBox(height: Gap.md),
      GlassCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Encerramento', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: Gap.md),
            Row(children: [
              Expanded(child: _num(_pesoPos, 'Peso pós (kg)')),
              const SizedBox(width: Gap.md),
              Expanded(child: _num(_ureiaPre, 'Ureia pré')),
              const SizedBox(width: Gap.md),
              Expanded(child: _num(_ureiaPos, 'Ureia pós')),
            ]),
            const SizedBox(height: Gap.lg),
            FilledButton(
              onPressed: widget.busy
                  ? null
                  : () {
                      final peso =
                          double.tryParse(_pesoPos.text.replaceAll(',', '.'));
                      if (peso == null) return;
                      widget.onEncerrar({
                        'peso_pos_kg': peso,
                        if (double.tryParse(_ureiaPre.text) != null)
                          'ureia_pre': double.parse(_ureiaPre.text),
                        if (double.tryParse(_ureiaPos.text) != null)
                          'ureia_pos': double.parse(_ureiaPos.text),
                      });
                    },
              child: const Text('Encerrar sessão'),
            ),
          ],
        ),
      ),
    ]);
  }

  Future<void> _dialogIntercorrencia() async {
    final tipo = TextEditingController();
    final conduta = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Intercorrência'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(
              controller: tipo,
              decoration: const InputDecoration(
                  labelText: 'Tipo (ex.: hipotensão, cãibra)')),
          const SizedBox(height: Gap.md),
          TextField(
              controller: conduta,
              decoration: const InputDecoration(labelText: 'Conduta')),
        ]),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancelar')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Registrar')),
        ],
      ),
    );
    if (ok == true && tipo.text.isNotEmpty) {
      await widget.onIntercorrencia({
        'tipo': tipo.text,
        if (conduta.text.isNotEmpty) 'conduta': conduta.text,
      });
    }
    tipo.dispose();
    conduta.dispose();
  }
}

// ------------------------- Resultado -------------------------
class _ResultadoCard extends StatelessWidget {
  final SessaoHD sessao;
  const _ResultadoCard({required this.sessao});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Última sessão — adequação',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.md),
          Row(children: [
            Expanded(
              child: VitalTile(
                label: 'Kt/V',
                value: sessao.ktv?.toStringAsFixed(2) ?? '—',
                status: sessao.ktv == null
                    ? null
                    : (sessao.ktv! >= 1.2 ? 'ok' : 'critical'),
              ),
            ),
            const SizedBox(width: Gap.md),
            Expanded(
              child: VitalTile(
                label: 'URR',
                value: sessao.urr?.toStringAsFixed(0) ?? '—',
                unit: '%',
                status: sessao.urr == null
                    ? null
                    : (sessao.urr! >= 65 ? 'ok' : 'warn'),
              ),
            ),
            const SizedBox(width: Gap.md),
            Expanded(
              child: VitalTile(
                label: 'UF real',
                value: sessao.ufRealL?.toStringAsFixed(1) ?? '—',
                unit: 'L',
              ),
            ),
          ]),
          for (final a in sessao.alertas) ...[
            const SizedBox(height: Gap.sm),
            StatusPill(label: a.mensagem, status: 'warn'),
          ],
        ],
      ),
    );
  }
}

// ------------------------- helpers -------------------------
Widget _num(TextEditingController c, String label) => TextField(
      controller: c,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration: InputDecoration(labelText: label),
    );

Widget _txt(TextEditingController c, String label) => TextField(
      controller: c,
      decoration: InputDecoration(labelText: label),
    );
