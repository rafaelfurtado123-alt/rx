import 'package:dio/dio.dart';

import 'token_storage.dart';

/// Cliente HTTP central (Dio) para a API Néfron.
///
/// Injeta o Bearer token automaticamente e normaliza erros da API em
/// [ApiException] com a mensagem `detail` retornada pelo FastAPI.
class ApiClient {
  final Dio dio;
  final TokenStorage _storage;

  ApiClient({required String baseUrl, TokenStorage? storage})
      : _storage = storage ?? TokenStorage(),
        dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 15),
          contentType: 'application/json',
        )) {
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        // Rotas de auth não exigem Bearer.
        if (!options.path.contains('/auth/')) {
          final token = await _storage.accessToken;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
        }
        handler.next(options);
      },
      onError: (e, handler) {
        handler.reject(_normalize(e));
      },
    ));
  }

  DioException _normalize(DioException e) {
    final data = e.response?.data;
    String message = 'Falha de conexão';
    if (data is Map && data['detail'] is String) {
      message = data['detail'] as String;
    } else if (data is Map && data['detail'] is List) {
      message = 'Dados inválidos';
    }
    return e.copyWith(error: ApiException(message, e.response?.statusCode));
  }
}

/// Erro de API já com mensagem amigável.
class ApiException implements Exception {
  final String message;
  final int? statusCode;
  const ApiException(this.message, this.statusCode);
  @override
  String toString() => message;
}
