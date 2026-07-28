import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'dashboard_models.dart';

/// Acesso à rota de dashboard.
class DashboardRepository {
  final Ref _ref;
  DashboardRepository(this._ref);

  Future<Dashboard> fetch() async {
    final api = _ref.read(apiClientProvider);
    final r = await api.dio.get('/api/v1/dashboard');
    return Dashboard.fromJson(r.data as Map<String, dynamic>);
  }
}

final dashboardRepositoryProvider =
    Provider<DashboardRepository>((ref) => DashboardRepository(ref));

/// Carrega o dashboard do perfil ativo.
final dashboardProvider = FutureProvider<Dashboard>((ref) {
  return ref.watch(dashboardRepositoryProvider).fetch();
});
