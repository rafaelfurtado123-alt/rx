import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'router.dart';
import 'theme/theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('pt_BR');
  runApp(const ProviderScope(child: NefronApp()));
}

/// Raiz do aplicativo Néfron.
///
/// Tema escuro por padrão com alternância automática pelo sistema. A navegação
/// é dirigida pela etapa de autenticação (ver [routerProvider]).
class NefronApp extends ConsumerWidget {
  const NefronApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Néfron',
      debugShowCheckedModeBanner: false,
      theme: NefronTheme.light(),
      darkTheme: NefronTheme.dark(),
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
