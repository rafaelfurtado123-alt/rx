import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../theme/theme.dart';
import '../../widgets/widgets.dart';
import 'auth_controller.dart';

/// Tela de verificação 2FA (passo 2). No primeiro acesso, mostra o QR code
/// para cadastrar o autenticador (TOTP).
class TwoFactorScreen extends ConsumerStatefulWidget {
  const TwoFactorScreen({super.key});

  @override
  ConsumerState<TwoFactorScreen> createState() => _TwoFactorScreenState();
}

class _TwoFactorScreenState extends ConsumerState<TwoFactorScreen> {
  final _code = TextEditingController();

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    if (_code.text.length != 6) return;
    await ref.read(authControllerProvider.notifier).verify2fa(_code.text.trim());
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    final c = context.colors;
    final enroll = auth.enrollment;

    return GlassScaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: BackButton(
          onPressed: () => ref.read(authControllerProvider.notifier).logout(),
        ),
        title: const Text('Verificação em duas etapas'),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Gap.xl),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: GlassCard(
              padding: const EdgeInsets.all(Gap.xl),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (enroll != null) ...[
                    Text('Configure seu autenticador',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: Gap.sm),
                    Text(
                      'Escaneie o QR code no Google Authenticator, Authy ou similar.',
                      textAlign: TextAlign.center,
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: c.textSecondary),
                    ),
                    const SizedBox(height: Gap.lg),
                    Container(
                      padding: const EdgeInsets.all(Gap.md),
                      decoration: const BoxDecoration(
                          color: Colors.white, borderRadius: Radii.rMd),
                      child: QrImageView(data: enroll.otpauthUri, size: 180),
                    ),
                    const SizedBox(height: Gap.sm),
                    _SecretCopy(secret: enroll.secret),
                    const Divider(height: Gap.xxxl),
                  ],
                  Text('Digite o código de 6 dígitos',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: Gap.lg),
                  TextField(
                    controller: _code,
                    autofocus: true,
                    keyboardType: TextInputType.number,
                    textAlign: TextAlign.center,
                    maxLength: 6,
                    style: NefronType.mono(color: c.textPrimary, size: 28),
                    inputFormatters: [
                      FilteringTextInputFormatter.digitsOnly,
                      LengthLimitingTextInputFormatter(6),
                    ],
                    decoration: const InputDecoration(
                        counterText: '', hintText: '000000'),
                    onChanged: (v) {
                      if (v.length == 6) _verify();
                    },
                  ),
                  if (auth.error != null) ...[
                    const SizedBox(height: Gap.md),
                    Text(auth.error!,
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: c.critical)),
                  ],
                  const SizedBox(height: Gap.lg),
                  FilledButton(
                    onPressed: auth.loading ? null : _verify,
                    child: auth.loading
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2))
                        : const Text('Verificar'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SecretCopy extends StatelessWidget {
  final String secret;
  const _SecretCopy({required this.secret});
  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return TextButton.icon(
      icon: const Icon(Icons.copy, size: 14),
      label: Text('Copiar chave manual',
          style: TextStyle(color: c.textSecondary, fontSize: 12)),
      onPressed: () => Clipboard.setData(ClipboardData(text: secret)),
    );
  }
}
