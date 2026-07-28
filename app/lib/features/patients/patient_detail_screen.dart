import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import 'patient_models.dart';
import 'patient_repository.dart';

/// Prontuário do paciente com abas: Linha do tempo, Exames, Evolução.
class PatientDetailScreen extends ConsumerWidget {
  final String pacienteId;
  const PatientDetailScreen({super.key, required this.pacienteId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final header = ref.watch(pacienteHeaderProvider(pacienteId));

    return DefaultTabController(
      length: 3,
      child: GlassScaffold(
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          leading: BackButton(onPressed: () => context.go('/pacientes')),
          title: header.maybeWhen(
            data: (h) => Text(h.nome),
            orElse: () => const Text('Prontuário'),
          ),
          bottom: const TabBar(tabs: [
            Tab(text: 'Linha do tempo'),
            Tab(text: 'Exames'),
            Tab(text: 'Evolução'),
          ]),
        ),
        floatingActionButton: _QuickActions(pacienteId: pacienteId),
        body: Column(
          children: [
            header.maybeWhen(
              data: (h) => _HeaderChips(header: h),
              orElse: () => const SizedBox.shrink(),
            ),
            const Expanded(
              child: TabBarView(children: [
                _TimelineTab(),
                _ExamesTab(),
                _EvolucaoTab(),
              ]),
            ),
          ],
        ),
      ),
    );
  }
}

/// FAB de ações frequentes (regra dos 2 cliques): Evolução, Prescrição HD, Sessão.
class _QuickActions extends StatelessWidget {
  final String pacienteId;
  const _QuickActions({required this.pacienteId});

  @override
  Widget build(BuildContext context) {
    return FloatingActionButton.extended(
      icon: const Icon(Icons.add),
      label: const Text('Ações'),
      onPressed: () => showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        builder: (ctx) => SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.notes_outlined),
                title: const Text('Nova evolução (SOAP)'),
                onTap: () {
                  Navigator.pop(ctx);
                  context.go('/pacientes/$pacienteId/evolucao');
                },
              ),
              ListTile(
                leading: const Icon(Icons.medication_outlined),
                title: const Text('Prescrição de HD'),
                onTap: () {
                  Navigator.pop(ctx);
                  context.go('/pacientes/$pacienteId/prescricao-hd');
                },
              ),
              ListTile(
                leading: const Icon(Icons.monitor_heart_outlined),
                title: const Text('Sessão de HD'),
                onTap: () {
                  Navigator.pop(ctx);
                  context.go('/pacientes/$pacienteId/sessao');
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HeaderChips extends StatelessWidget {
  final PacienteHeader header;
  const _HeaderChips({required this.header});
  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final chips = <Widget>[
      if (header.idade != null) _chip(context, '${header.idade} anos'),
      if (header.estagioDrc != null) _chip(context, 'DRC E${header.estagioDrc}'),
      if (header.turnoDialise != null) _chip(context, header.turnoDialise!),
      for (final a in header.alergias)
        _chip(context, 'Alergia: $a', color: c.critical),
    ];
    return Padding(
      padding: const EdgeInsets.fromLTRB(Gap.lg, Gap.sm, Gap.lg, 0),
      child: Wrap(spacing: Gap.sm, runSpacing: Gap.sm, children: chips),
    );
  }

  Widget _chip(BuildContext context, String label, {Color? color}) {
    final c = context.colors;
    final col = color ?? c.textSecondary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: Gap.md, vertical: Gap.xs),
      decoration: BoxDecoration(
        color: col.withValues(alpha: 0.12),
        borderRadius: const BorderRadius.all(Radius.circular(Radii.pill)),
      ),
      child: Text(label,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(color: col)),
    );
  }
}

// ------------------------------- Timeline -------------------------------
class _TimelineTab extends ConsumerWidget {
  const _TimelineTab();
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final id = _pacienteId(context);
    final async = ref.watch(timelineProvider(id));
    return async.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('$e')),
      data: (itens) => itens.isEmpty
          ? const _Vazio('Sem registros ainda')
          : ListView.separated(
              padding: const EdgeInsets.all(Gap.lg),
              itemCount: itens.length,
              separatorBuilder: (_, __) => const SizedBox(height: Gap.sm),
              itemBuilder: (context, i) => _TimelineCard(item: itens[i]),
            ),
    );
  }
}

class _TimelineCard extends StatelessWidget {
  final TimelineItem item;
  const _TimelineCard({required this.item});
  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final icon = switch (item.tipo) {
      'exame' => Icons.science_outlined,
      'evolucao' => Icons.notes_outlined,
      _ => Icons.medical_services_outlined,
    };
    return GlassCard(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: c.primary, size: 20),
          const SizedBox(width: Gap.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.titulo,
                    style: Theme.of(context).textTheme.titleMedium),
                if (item.detalhe != null)
                  Text(item.detalhe!,
                      style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: Gap.xs),
                Text(DateFormat('dd/MM/yyyy HH:mm').format(item.data.toLocal()),
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: c.textSecondary)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ------------------------------- Exames -------------------------------
class _ExamesTab extends ConsumerWidget {
  const _ExamesTab();
  // Séries clínicas-chave do PCDT (anemia + DMO + adequação)
  static const _codigos = ['HB', 'FERR', 'TSAT', 'PTH', 'CA', 'P', 'KTV'];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final id = _pacienteId(context);
    return ListView(
      padding: const EdgeInsets.all(Gap.lg),
      children: [
        for (final cod in _codigos) ...[
          _SerieCard(pacienteId: id, codigo: cod),
          const SizedBox(height: Gap.md),
        ],
      ],
    );
  }
}

class _SerieCard extends ConsumerWidget {
  final String pacienteId;
  final String codigo;
  const _SerieCard({required this.pacienteId, required this.codigo});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async =
        ref.watch(serieExameProvider((pacienteId: pacienteId, codigo: codigo)));
    return async.when(
      loading: () => const SizedBox(
          height: 80, child: Center(child: CircularProgressIndicator())),
      // Exame não catalogado/sem dados: oculta silenciosamente.
      error: (_, __) => const SizedBox.shrink(),
      data: (serie) =>
          serie.pontos.isEmpty ? const SizedBox.shrink() : TrendChart(serie: serie),
    );
  }
}

// ------------------------------- Evolução -------------------------------
class _EvolucaoTab extends ConsumerWidget {
  const _EvolucaoTab();
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final id = _pacienteId(context);
    final async = ref.watch(evolucoesProvider(id));
    return async.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('$e')),
      data: (evolucoes) => evolucoes.isEmpty
          ? const _Vazio('Nenhuma evolução registrada')
          : ListView.separated(
              padding: const EdgeInsets.all(Gap.lg),
              itemCount: evolucoes.length,
              separatorBuilder: (_, __) => const SizedBox(height: Gap.sm),
              itemBuilder: (context, i) => _EvolucaoCard(ev: evolucoes[i]),
            ),
    );
  }
}

class _EvolucaoCard extends StatelessWidget {
  final Evolucao ev;
  const _EvolucaoCard({required this.ev});
  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(ev.categoria.toUpperCase(),
                    style: Theme.of(context)
                        .textTheme
                        .labelLarge
                        ?.copyWith(color: c.primary)),
              ),
              StatusPill(
                label: ev.assinada ? 'Assinada' : 'Rascunho',
                status: ev.assinada ? 'ok' : 'warn',
              ),
            ],
          ),
          const SizedBox(height: Gap.sm),
          if (ev.subjetivo != null) _linha(context, 'S', ev.subjetivo!),
          if (ev.objetivo != null) _linha(context, 'O', ev.objetivo!),
          if (ev.avaliacao != null) _linha(context, 'A', ev.avaliacao!),
          if (ev.plano != null) _linha(context, 'P', ev.plano!),
          if (ev.textoLivre != null) Text(ev.textoLivre!),
          const SizedBox(height: Gap.xs),
          Text(DateFormat('dd/MM/yyyy HH:mm').format(ev.createdAt.toLocal()),
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: c.textSecondary)),
        ],
      ),
    );
  }

  Widget _linha(BuildContext context, String tag, String texto) {
    final c = context.colors;
    return Padding(
      padding: const EdgeInsets.only(bottom: 2),
      child: RichText(
        text: TextSpan(
          style: Theme.of(context).textTheme.bodyMedium,
          children: [
            TextSpan(
                text: '$tag: ',
                style: TextStyle(fontWeight: FontWeight.w700, color: c.primary)),
            TextSpan(text: texto),
          ],
        ),
      ),
    );
  }
}

class _Vazio extends StatelessWidget {
  final String texto;
  const _Vazio(this.texto);
  @override
  Widget build(BuildContext context) => Center(
        child: Text(texto,
            style: TextStyle(color: context.colors.textSecondary)),
      );
}

/// Recupera o id do paciente da rota atual (as abas são filhas da tela de detalhe).
String _pacienteId(BuildContext context) {
  final state = GoRouterState.of(context);
  return state.pathParameters['id']!;
}
