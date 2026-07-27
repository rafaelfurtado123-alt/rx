/// Modelos de autenticação (espelham os DTOs do FastAPI).

class LoginResult {
  final String mfaToken;
  final bool totpEnrollmentRequired;
  const LoginResult({required this.mfaToken, required this.totpEnrollmentRequired});

  factory LoginResult.fromJson(Map<String, dynamic> j) => LoginResult(
        mfaToken: j['mfa_token'] as String,
        totpEnrollmentRequired: j['totp_enrollment_required'] as bool? ?? false,
      );
}

class TotpEnrollment {
  final String secret;
  final String otpauthUri;
  const TotpEnrollment({required this.secret, required this.otpauthUri});

  factory TotpEnrollment.fromJson(Map<String, dynamic> j) => TotpEnrollment(
        secret: j['secret'] as String,
        otpauthUri: j['otpauth_uri'] as String,
      );
}

class Vinculo {
  final String unidadeId;
  final String unidadeNome;
  final String papel;
  const Vinculo(
      {required this.unidadeId, required this.unidadeNome, required this.papel});

  factory Vinculo.fromJson(Map<String, dynamic> j) => Vinculo(
        unidadeId: j['unidade_id'] as String,
        unidadeNome: j['unidade_nome'] as String,
        papel: j['papel'] as String,
      );
}

class Verify2FAResult {
  final String refreshToken;
  final List<Vinculo> vinculos;
  const Verify2FAResult({required this.refreshToken, required this.vinculos});

  factory Verify2FAResult.fromJson(Map<String, dynamic> j) => Verify2FAResult(
        refreshToken: j['refresh_token'] as String,
        vinculos: (j['vinculos'] as List)
            .map((e) => Vinculo.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class SessionTokens {
  final String accessToken;
  final String refreshToken;
  final String unidadeId;
  final String papel;
  const SessionTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.unidadeId,
    required this.papel,
  });

  factory SessionTokens.fromJson(Map<String, dynamic> j) => SessionTokens(
        accessToken: j['access_token'] as String,
        refreshToken: j['refresh_token'] as String,
        unidadeId: j['unidade_id'] as String,
        papel: j['papel'] as String,
      );
}
