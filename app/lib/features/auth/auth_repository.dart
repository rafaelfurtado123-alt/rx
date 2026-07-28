import '../../core/api_client.dart';
import 'auth_models.dart';

/// Acesso às rotas de autenticação do FastAPI.
class AuthRepository {
  final ApiClient _api;
  AuthRepository(this._api);

  Future<LoginResult> login(String email, String senha) async {
    final r = await _api.dio.post('/api/v1/auth/login',
        data: {'email': email, 'senha': senha});
    return LoginResult.fromJson(r.data as Map<String, dynamic>);
  }

  Future<TotpEnrollment> enrollTotp(String mfaToken) async {
    final r = await _api.dio
        .post('/api/v1/auth/2fa/enroll', queryParameters: {'mfa_token': mfaToken});
    return TotpEnrollment.fromJson(r.data as Map<String, dynamic>);
  }

  Future<Verify2FAResult> verify2fa(String mfaToken, String codigo) async {
    final r = await _api.dio.post('/api/v1/auth/2fa/verify',
        data: {'mfa_token': mfaToken, 'codigo': codigo});
    return Verify2FAResult.fromJson(r.data as Map<String, dynamic>);
  }

  Future<SessionTokens> selectContext(
      String refreshToken, String unidadeId, String papel) async {
    final r = await _api.dio.post('/api/v1/auth/context', data: {
      'refresh_token': refreshToken,
      'unidade_id': unidadeId,
      'papel': papel,
    });
    return SessionTokens.fromJson(r.data as Map<String, dynamic>);
  }
}
