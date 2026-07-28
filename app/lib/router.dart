import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'features/auth/auth_controller.dart';
import 'features/auth/login_screen.dart';
import 'features/auth/select_context_screen.dart';
import 'features/auth/two_factor_screen.dart';
import 'features/dashboard/dashboard_screen.dart';
import 'features/hd/hd_prescription_screen.dart';
import 'features/hd/session_screen.dart';
import 'features/patients/patient_detail_screen.dart';
import 'features/patients/patients_list_screen.dart';
import 'features/patients/soap_editor_screen.dart';

const _authRoutes = {'/login', '/2fa', '/select-context'};

/// Roteador com redirecionamento baseado na etapa de autenticação.
final routerProvider = Provider<GoRouter>((ref) {
  final notifier = _AuthListenable(ref);

  return GoRouter(
    initialLocation: '/login',
    refreshListenable: notifier,
    redirect: (context, state) {
      final stage = ref.read(authControllerProvider).stage;
      final loc = state.matchedLocation;

      // Fluxo de autenticação incompleto: força a etapa correspondente.
      if (stage != AuthStage.authenticated) {
        final dest = switch (stage) {
          AuthStage.unauthenticated => '/login',
          AuthStage.awaiting2fa => '/2fa',
          AuthStage.selectingContext => '/select-context',
          AuthStage.authenticated => '/dashboard',
        };
        return loc == dest ? null : dest;
      }

      // Autenticado: sai das telas de auth; caso contrário, navega livremente.
      if (_authRoutes.contains(loc)) return '/dashboard';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/2fa', builder: (_, __) => const TwoFactorScreen()),
      GoRoute(
          path: '/select-context', builder: (_, __) => const SelectContextScreen()),
      GoRoute(path: '/dashboard', builder: (_, __) => const DashboardScreen()),
      GoRoute(path: '/pacientes', builder: (_, __) => const PatientsListScreen()),
      GoRoute(
        path: '/pacientes/:id',
        builder: (_, s) =>
            PatientDetailScreen(pacienteId: s.pathParameters['id']!),
      ),
      GoRoute(
        path: '/pacientes/:id/evolucao',
        builder: (_, s) => SoapEditorScreen(pacienteId: s.pathParameters['id']!),
      ),
      GoRoute(
        path: '/pacientes/:id/prescricao-hd',
        builder: (_, s) =>
            HdPrescriptionScreen(pacienteId: s.pathParameters['id']!),
      ),
      GoRoute(
        path: '/pacientes/:id/sessao',
        builder: (_, s) => SessionScreen(pacienteId: s.pathParameters['id']!),
      ),
    ],
  );
});

/// Adapta o StateNotifier de auth para um Listenable do go_router.
class _AuthListenable extends ChangeNotifier {
  _AuthListenable(Ref ref) {
    ref.listen(authControllerProvider, (_, __) => notifyListeners());
  }
}
