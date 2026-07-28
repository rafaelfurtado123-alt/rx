import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/auth/auth_repository.dart';
import 'api_client.dart';
import 'token_storage.dart';

/// URL base da API.
///
/// Ordem de resolução:
///   1. --dart-define=API_BASE_URL=... no build (quando informado);
///   2. na web, o PRÓPRIO domínio da página (o nginx do deploy faz o proxy
///      de /api) — assim UM único build serve qualquer domínio;
///   3. localhost:8000 (desenvolvimento desktop/mobile).
const _apiBaseUrlDefine = String.fromEnvironment('API_BASE_URL');

String get _apiBaseUrl {
  if (_apiBaseUrlDefine.isNotEmpty) return _apiBaseUrlDefine;
  if (kIsWeb) return Uri.base.origin;
  return 'http://localhost:8000';
}

final tokenStorageProvider = Provider<TokenStorage>((ref) => TokenStorage());

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient(
      baseUrl: _apiBaseUrl,
      storage: ref.watch(tokenStorageProvider),
    ));

final authRepositoryProvider =
    Provider<AuthRepository>((ref) => AuthRepository(ref.watch(apiClientProvider)));
