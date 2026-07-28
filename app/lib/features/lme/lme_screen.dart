import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/providers.dart';
import '../../theme/theme.dart';
import '../../widgets/vidaas_dialog.dart';
import '../../widgets/widgets.dart';
import 'lme_models.dart';
import 'lme_repository.dart';

/// LME Inteligente: histórico de laudos + geração guiada em ≤30s.
class LmeScreen extends ConsumerStatefulWidget {
  final String pacienteId;
  const LmeScreen({super.key, required this.pacienteId});

  @override
  ConsumerState<LmeScreen> createState() => _LmeScreenState();
}

class _LmeScreenState extends ConsumerState<LmeScreen> {
  bool _busy = false;
  String? _error;
  Laudo? _emGeracao; // rascunho recém-gerado em revisão

  Future<void> _gerar(String medicamentoId, String? posologia) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final laudo = await ref.read(lmeRepositoryProvider).gerar(
          widget.pacienteId, {
        'medicamento_id': medicamentoId,
        if (posologia != null && posologia.isNotEmpty) 'posologia': posologia,
      });
      setState(() => _emGeracao = laudo);
      ref.invalidate(lmesProvider(widget.pacienteId));
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _assinar(Laudo laudo) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final emitido =
          await ref.read(lmeRepositoryProvider).assinar(laudo.id);
      setState(() => _emGeracao = emitido);
      ref.invalidate(lmesProvider(widget.pacienteId));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('LME emitido — válido até '
                '${DateFormat('dd/MM/yyyy').format(emitido.validoAte!.toLocal())}')));
      }
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Assinatura ICP-Brasil em nuvem (VIDaaS/CRM Digital):
  /// autoriza no app do médico (QR/push) → assina o PDF do laudo.
  Future<void> _assinarIcp(Laudo laudo) async {
    final repo = ref.read(lmeRepositoryProvider);
    Map<String, dynamic> auth;
    try {
      auth = await repo.vidaasAutorizar();
    } catch (e) {
      setState(() => _error = '$e');
      return;
    }
    if (!mounted) return;

    final state = auth['state'] as String;
    final url = auth['authorization_url'] as String;
    final isMock = auth['mock'] as bool? ?? false;

    final autorizado = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => VidaasDialog(
        authorizationUrl: url,
        isMock: isMock,
        checkReady: () async => await repo.vidaasStatus(state) == 'autorizada',
        simularAprovacao: isMock
            ? () => ref.read(apiClientProvider).dio.get(
                '/api/v1/assinatura/vidaas/callback',
                queryParameters: {'state': state, 'code': 'DEMO'})
            : null,
      ),
    );
    if (autorizado != true || !mounted) return;

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final resultado = await repo.vidaasAssinarLme(laudo.id);
      ref.invalidate(lmesProvider(widget.pacienteId));
      if (mounted) {
        final cert = resultado['certificado'] as Map<String, dynamic>?;
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('LME assinado com ICP-Brasil '
                '(${cert?['origem'] ?? 'vidaas'}) ✓')));
      }
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _renovar(Laudo laudo) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final novo = await ref.read(lmeRepositoryProvider).renovar(laudo.id);
      setState(() => _emGeracao = novo);
      ref.invalidate(lmesProvider(widget.pacienteId));
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final lmes = ref.watch(lmesProvider(widget.pacienteId));

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(
            onPressed: () => context.go('/pacientes/${widget.pacienteId}')),
        title: const Text('LME Inteligente'),
      ),
      floatingActionButton: _emGeracao == null
          ? FloatingActionButton.extended(
              icon: const Icon(Icons.description_outlined),
              label: const Text('Gerar LME'),
              onPressed: _busy ? null : () => _abrirSeletorMedicamento(),
            )
          : null,
      body: ListView(
        padding: const EdgeInsets.all(Gap.lg),
        children: [
          if (_error != null) ...[
            GlassCard(
                child: Text(_error!, style: TextStyle(color: c.critical))),
            const SizedBox(height: Gap.md),
          ],
          if (_emGeracao != null) ...[
            _RevisaoCard(
              laudo: _emGeracao!,
              busy: _busy,
              onAssinar: () => _assinar(_emGeracao!),
              onAssinarIcp: () => _assinarIcp(_emGeracao!),
              onFechar: () => setState(() => _emGeracao = null),
            ),
            const SizedBox(height: Gap.lg),
          ],
          Text('Histórico de LMEs',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: Gap.md),
          lmes.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Text('$e'),
            data: (lista) => lista.isEmpty
                ? Text('Nenhum LME emitido',
                    style: TextStyle(color: c.textSecondary))
                : Column(children: [
                    for (final l in lista) ...[
                      _LaudoCard(
                          laudo: l,
                          busy: _busy,
                          onRenovar: () => _renovar(l),
                          onRevisar: () => setState(() => _emGeracao = l)),
                      const SizedBox(height: Gap.sm),
                    ],
                  ]),
          ),
        ],
      ),
    );
  }

  Future<void> _abrirSeletorMedicamento() async {
    final api = ref.read(apiClientProvider);
    final r = await api.dio
        .get('/api/v1/medicamentos', queryParameters: {'ceaf': true});
    final meds = (r.data as List).cast<Map<String, dynamic>>();
    if (!mounted) return;

    final posologia = TextEditingController();
    String? selecionado;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) => Padding(
          padding: EdgeInsets.only(
              left: Gap.lg,
              right: Gap.lg,
              bottom: MediaQuery.of(ctx).viewInsets.bottom + Gap.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Medicamento CEAF',
                  style: Theme.of(ctx).textTheme.titleMedium),
              const SizedBox(height: Gap.md),
              for (final m in meds)
                RadioListTile<String>(
                  value: m['id'] as String,
                  groupValue: selecionado,
                  title: Text(m['principio_ativo'] as String),
                  subtitle: Text(m['apresentacao'] as String),
                  onChanged: (v) => setSheet(() => selecionado = v),
                ),
              const SizedBox(height: Gap.md),
              TextField(
                  controller: posologia,
                  decoration: const InputDecoration(
                      labelText: 'Posologia (ex.: 4000 UI 3x/semana SC)')),
              const SizedBox(height: Gap.lg),
              FilledButton(
                onPressed: selecionado == null
                    ? null
                    : () {
                        Navigator.pop(ctx);
                        _gerar(selecionado!, posologia.text);
                      },
                child: const Text('Gerar com autopreenchimento'),
              ),
              const SizedBox(height: Gap.md),
            ],
          ),
        ),
      ),
    );
    posologia.dispose();
  }
}

/// Card de revisão do laudo em geração: checagem de exames + textos + emissão.
class _RevisaoCard extends StatelessWidget {
  final Laudo laudo;
  final bool busy;
  final VoidCallback onAssinar;
  final VoidCallback? onAssinarIcp;
  final VoidCallback onFechar;
  const _RevisaoCard(
      {required this.laudo,
      required this.busy,
      required this.onAssinar,
      this.onAssinarIcp,
      required this.onFechar});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(
                child: Text('${laudo.medicamento} — revisão',
                    style: Theme.of(context).textTheme.titleMedium)),
            IconButton(icon: const Icon(Icons.close), onPressed: onFechar),
          ]),
          if (laudo.pcdtNome != null)
            Text('PCDT: ${laudo.pcdtNome} (v${laudo.pcdtVersao})',
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: c.textSecondary)),
          const SizedBox(height: Gap.sm),
          Wrap(spacing: Gap.sm, runSpacing: Gap.sm, children: [
            if (laudo.cidPrincipal != null)
              StatusPill(label: 'CID ${laudo.cidPrincipal}', status: 'info'),
            for (final cid in laudo.cidsSecundarios)
              StatusPill(label: cid, status: 'info'),
          ]),
          const Divider(height: Gap.xxl),
          Text('Exames obrigatórios do PCDT',
              style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: Gap.sm),
          for (final e in laudo.exames) _ExameLinha(exame: e),
          if (laudo.pendencias.isNotEmpty) ...[
            const SizedBox(height: Gap.md),
            for (final p in laudo.pendencias)
              Row(children: [
                Icon(Icons.error_outline, size: 16, color: c.critical),
                const SizedBox(width: Gap.sm),
                Expanded(
                    child:
                        Text(p, style: TextStyle(color: c.critical, fontSize: 13))),
              ]),
          ],
          const Divider(height: Gap.xxl),
          Text('Anamnese (gerada — revisável)',
              style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: Gap.xs),
          Text(laudo.anamnese ?? '—',
              style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: Gap.md),
          Text('Justificativa clínica (alinhada ao PCDT)',
              style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: Gap.xs),
          Text(laudo.justificativa ?? '—',
              style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: Gap.lg),
          if (laudo.status == 'rascunho')
            FilledButton.icon(
              icon: const Icon(Icons.draw_outlined),
              onPressed: (busy || !laudo.podeEmitir) ? null : onAssinar,
              label: Text(laudo.podeEmitir
                  ? 'Assinar e emitir (validade 90 dias)'
                  : 'Resolva as pendências para emitir'),
            ),
          if (laudo.vigente) ...[
            StatusPill(
                label:
                    'Vigente — ${laudo.diasRestantes} dias restantes',
                status: 'ok'),
            if (onAssinarIcp != null) ...[
              const SizedBox(height: Gap.md),
              OutlinedButton.icon(
                icon: const Icon(Icons.verified_outlined),
                onPressed: busy ? null : onAssinarIcp,
                label: const Text('Assinar com ICP-Brasil (VIDaaS)'),
              ),
            ],
          ],
        ],
      ),
    );
  }
}

/// Linha de checagem de um exame obrigatório do PCDT (✓ presente / ⚠ vencido /
/// ✕ ausente) com valor e data em fonte tabular.
class _ExameLinha extends StatelessWidget {
  final ExameChecagem exame;
  const _ExameLinha({required this.exame});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final (icone, cor) = switch (exame.situacao) {
      'presente' => (Icons.check_circle_outline, c.ok),
      'vencido' => (Icons.history_toggle_off, c.warn),
      _ => (Icons.cancel_outlined, c.critical),
    };
    final valor = exame.valor != null
        ? '${exame.valor} ${exame.unidade ?? ''}'.trim()
        : '—';
    final data = exame.dataColeta != null
        ? DateFormat('dd/MM/yyyy').format(exame.dataColeta!.toLocal())
        : '';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(children: [
        Icon(icone, size: 16, color: cor),
        const SizedBox(width: Gap.sm),
        Expanded(child: Text(exame.nome)),
        Text('$valor  $data',
            style: NefronType.mono(color: c.textSecondary, size: 12)),
      ]),
    );
  }
}

/// Card do histórico com status, validade e renovação em 1 clique.
class _LaudoCard extends StatelessWidget {
  final Laudo laudo;
  final bool busy;
  final VoidCallback onRenovar;
  final VoidCallback onRevisar;
  const _LaudoCard(
      {required this.laudo,
      required this.busy,
      required this.onRenovar,
      required this.onRevisar});

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final status = switch (laudo.status) {
      'vigente' => (laudo.diasRestantes ?? 99) <= 15 ? 'warn' : 'ok',
      'vencido' => 'critical',
      'rascunho' => 'warn',
      _ => 'info',
    };
    final validade = laudo.validoAte != null
        ? 'até ${DateFormat('dd/MM/yyyy').format(laudo.validoAte!.toLocal())}'
        : '';
    return GlassCard(
      onTap: onRevisar,
      child: Row(children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(laudo.medicamento,
                style: Theme.of(context).textTheme.titleMedium),
            Text(
                '${laudo.status.toUpperCase()} $validade'
                '${laudo.laudoAnteriorId != null ? ' · renovação' : ''}',
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: c.textSecondary)),
          ]),
        ),
        StatusPill(label: laudo.status, status: status),
        if (laudo.status == 'vigente' || laudo.status == 'vencido') ...[
          const SizedBox(width: Gap.sm),
          IconButton(
            tooltip: 'Renovar (1 clique)',
            icon: Icon(Icons.autorenew, color: c.primary),
            onPressed: busy ? null : onRenovar,
          ),
        ],
      ]),
    );
  }
}
