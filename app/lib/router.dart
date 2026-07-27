import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'features/auth/auth_controller.dart';
import 'features/auth/login_screen.dart';
import 'features/auth/select_context_screen.dart';
import 'features/auth/two_factor_screen.dart';
import 'features/dashboard/dashboard_screen.dart';

/// Roteador com redirecionamento baseado na etapa de autenticação.
///
/// O `refreshListenable` observa o [AuthController], de modo que qualquer
/// mudança de etapa reavalia as rotas automaticamente.
final routerProvider = Provider<GoRouter>((ref) {
  final notifier = _AuthListenable(ref);

  return GoRouter(
    initialLocation: '/login',
    refreshListenable: notifier,
    redirect: (context, state) {
      final stage = ref.read(authControllerProvider).stage;
      final loc = state.matchedLocation;
      final dest = switch (stage) {
        AuthStage.unauthenticated => '/login',
        AuthStage.awaiting2fa => '/2fa',
        AuthStage.selectingContext => '/select-context',
        AuthStage.authenticated => '/dashboard',
      };
      return loc == dest ? null : dest;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/2fa', builder: (_, __) => const TwoFactorScreen()),
      GoRoute(
          path: '/select-context', builder: (_, __) => const SelectContextScreen()),
      GoRoute(path: '/dashboard', builder: (_, __) => const DashboardScreen()),
    ],
  );
});

/// Adapta o StateNotifier de auth para um Listenable do go_router.
class _AuthListenable extends ChangeNotifier {
  _AuthListenable(Ref ref) {
    ref.listen(authControllerProvider, (_, __) => notifyListeners());
  }
}
