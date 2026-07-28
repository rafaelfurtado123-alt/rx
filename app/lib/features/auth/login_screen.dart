import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../theme/theme.dart';
import '../../widgets/vidaas_dialog.dart';
import '../../widgets/widgets.dart';
import 'auth_controller.dart';
import 'auth_models.dart';

/// Tela de login (passo 1: e-mail + senha).
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _senha = TextEditingController();
  bool _obscure = true;

  @override
  void dispose() {
    _email.dispose();
    _senha.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    await ref.read(authControllerProvider.notifier).login(
          _email.text.trim(),
          _senha.text,
        );
  }

  /// Login por certificado digital em nuvem (VIDaaS/CRM Digital):
  /// CPF → aprovação no app do PSC → tokens (dispensa senha e TOTP).
  Future<void> _loginComCertificado() async {
    final cpfCtl = TextEditingController();
    final cpf = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Login com certificado digital'),
        content: TextField(
          controller: cpfCtl,
          autofocus: true,
          keyboardType: TextInputType.number,
          maxLength: 11,
          decoration: const InputDecoration(
              labelText: 'CPF do titular do certificado', counterText: ''),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancelar')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, cpfCtl.text.trim()),
              child: const Text('Continuar')),
        ],
      ),
    );
    cpfCtl.dispose();
    if (cpf == null || cpf.isEmpty || !mounted) return;

    final dio = ref.read(apiClientProvider).dio;
    Map<String, dynamic> auth;
    try {
      final r = await dio.post('/api/v1/auth/vidaas/login', data: {'cpf': cpf});
      auth = r.data as Map<String, dynamic>;
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
      return;
    }
    if (!mounted) return;

    final state = auth['state'] as String;
    Verify2FAResult? tokens;
    final ok = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => VidaasDialog(
        authorizationUrl: auth['authorization_url'] as String,
        isMock: auth['mock'] as bool? ?? false,
        subtitle: 'Aprove o LOGIN no aplicativo VIDaaS. A aprovação com seu '
            'certificado ICP-Brasil substitui senha e código 2FA.',
        checkReady: () async {
          final r = await dio.get('/api/v1/auth/vidaas/login/$state');
          final data = r.data as Map<String, dynamic>;
          if (data['status'] == 'autorizada' && data['refresh_token'] != null) {
            tokens = Verify2FAResult.fromJson(data);
            return true;
          }
          return false;
        },
        simularAprovacao: (auth['mock'] as bool? ?? false)
            ? () => dio.get('/api/v1/assinatura/vidaas/callback',
                queryParameters: {'state': state, 'code': 'DEMO'})
            : null,
      ),
    );
    if (ok == true && tokens != null && mounted) {
      await ref.read(authControllerProvider.notifier).adoptVidaasLogin(tokens!);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    final c = context.colors;

    return GlassScaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Gap.xl),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('néfron·',
                    style: Theme.of(context)
                        .textTheme
                        .displaySmall
                        ?.copyWith(color: c.primary)),
                Text('Prontuário Nefrológico',
                    style: Theme.of(context)
                        .textTheme
                        .bodyLarge
                        ?.copyWith(color: c.textSecondary)),
                const SizedBox(height: Gap.xxl),
                GlassCard(
                  padding: const EdgeInsets.all(Gap.xl),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      children: [
                        TextFormField(
                          controller: _email,
                          keyboardType: TextInputType.emailAddress,
                          autofillHints: const [AutofillHints.username],
                          decoration: const InputDecoration(
                              labelText: 'E-mail / CRM',
                              prefixIcon: Icon(Icons.person_outline)),
                          validator: (v) =>
                              (v == null || !v.contains('@')) ? 'Informe o e-mail' : null,
                        ),
                        const SizedBox(height: Gap.lg),
                        TextFormField(
                          controller: _senha,
                          obscureText: _obscure,
                          autofillHints: const [AutofillHints.password],
                          onFieldSubmitted: (_) => _submit(),
                          decoration: InputDecoration(
                            labelText: 'Senha',
                            prefixIcon: const Icon(Icons.lock_outline),
                            suffixIcon: IconButton(
                              icon: Icon(_obscure
                                  ? Icons.visibility_off_outlined
                                  : Icons.visibility_outlined),
                              onPressed: () => setState(() => _obscure = !_obscure),
                            ),
                          ),
                          validator: (v) =>
                              (v == null || v.length < 6) ? 'Mínimo 6 caracteres' : null,
                        ),
                        if (auth.error != null) ...[
                          const SizedBox(height: Gap.md),
                          _ErrorText(auth.error!),
                        ],
                        const SizedBox(height: Gap.xl),
                        FilledButton(
                          onPressed: auth.loading ? null : _submit,
                          child: auth.loading
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2))
                              : const Text('Entrar'),
                        ),
                        const SizedBox(height: Gap.md),
                        Row(children: [
                          Expanded(child: Divider(color: c.glassStroke)),
                          Padding(
                            padding: const EdgeInsets.symmetric(
                                horizontal: Gap.md),
                            child: Text('ou',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(color: c.textSecondary)),
                          ),
                          Expanded(child: Divider(color: c.glassStroke)),
                        ]),
                        const SizedBox(height: Gap.md),
                        OutlinedButton.icon(
                          icon: const Icon(Icons.verified_user_outlined),
                          onPressed:
                              auth.loading ? null : _loginComCertificado,
                          label: const Text(
                              'Entrar com certificado digital (VIDaaS)'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: Gap.lg),
                Text('Ao continuar, você concorda com o registro de acesso (LGPD).',
                    textAlign: TextAlign.center,
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: c.textSecondary)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ErrorText extends StatelessWidget {
  final String message;
  const _ErrorText(this.message);
  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Row(
      children: [
        Icon(Icons.error_outline, size: 16, color: c.critical),
        const SizedBox(width: Gap.sm),
        Expanded(
          child: Text(message,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: c.critical)),
        ),
      ],
    );
  }
}
