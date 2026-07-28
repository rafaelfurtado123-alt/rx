import 'dart:async';

import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../theme/theme.dart';

/// Diálogo de autorização no VIDaaS (certificado em nuvem do CRM Digital):
/// mostra QR/URL, faz polling via [checkReady] e fecha com `true` quando a
/// sessão é aprovada no app do PSC. Compartilhado por login, LME e receitas.
class VidaasDialog extends StatefulWidget {
  final String authorizationUrl;
  final bool isMock;
  final String subtitle;

  /// Retorna `true` quando a autorização foi concluída.
  final Future<bool> Function() checkReady;

  /// Demonstração: simula a aprovação no PSC (apenas em modo mock).
  final Future<void> Function()? simularAprovacao;

  const VidaasDialog({
    super.key,
    required this.authorizationUrl,
    required this.checkReady,
    this.isMock = false,
    this.subtitle =
        'Aprove a sessão no aplicativo VIDaaS (certificado do CRM Digital) '
        'escaneando o QR code ou abrindo o link.',
    this.simularAprovacao,
  });

  @override
  State<VidaasDialog> createState() => _VidaasDialogState();
}

class _VidaasDialogState extends State<VidaasDialog> {
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 2), (_) => _verificar());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _verificar() async {
    try {
      if (await widget.checkReady() && mounted) {
        _timer?.cancel();
        Navigator.pop(context, true);
      }
    } catch (_) {
      // erro transitório de rede: mantém o polling
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return AlertDialog(
      title: const Text('Autorize no app VIDaaS'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(widget.subtitle, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: Gap.lg),
          Container(
            padding: const EdgeInsets.all(Gap.md),
            decoration: const BoxDecoration(
                color: Colors.white, borderRadius: Radii.rMd),
            child: QrImageView(data: widget.authorizationUrl, size: 160),
          ),
          const SizedBox(height: Gap.sm),
          SelectableText(widget.authorizationUrl,
              maxLines: 2,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: c.textSecondary)),
          const SizedBox(height: Gap.md),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            SizedBox(
                height: 14,
                width: 14,
                child: CircularProgressIndicator(
                    strokeWidth: 2, color: c.primary)),
            const SizedBox(width: Gap.sm),
            Text('Aguardando autorização…',
                style: Theme.of(context).textTheme.bodySmall),
          ]),
          if (widget.isMock && widget.simularAprovacao != null) ...[
            const SizedBox(height: Gap.md),
            TextButton(
              onPressed: () => widget.simularAprovacao!(),
              child: const Text('Ambiente de demonstração: simular aprovação'),
            ),
          ],
        ],
      ),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar')),
      ],
    );
  }
}
