import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/token_storage.dart';
import 'auth_models.dart';
import 'auth_repository.dart';

/// Etapas do fluxo de login.
enum AuthStage { unauthenticated, awaiting2fa, selectingContext, authenticated }

/// Estado imutável da autenticação.
class AuthState {
  final AuthStage stage;
  final bool loading;
  final String? error;

  // Dados intermediários do fluxo
  final String? mfaToken;
  final bool totpEnrollmentRequired;
  final TotpEnrollment? enrollment;
  final String? refreshToken;
  final List<Vinculo> vinculos;

  // Contexto ativo (após concluir)
  final String? papel;
  final String? unidadeId;

  const AuthState({
    this.stage = AuthStage.unauthenticated,
    this.loading = false,
    this.error,
    this.mfaToken,
    this.totpEnrollmentRequired = false,
    this.enrollment,
    this.refreshToken,
    this.vinculos = const [],
    this.papel,
    this.unidadeId,
  });

  AuthState copyWith({
    AuthStage? stage,
    bool? loading,
    String? error,
    String? mfaToken,
    bool? totpEnrollmentRequired,
    TotpEnrollment? enrollment,
    String? refreshToken,
    List<Vinculo>? vinculos,
    String? papel,
    String? unidadeId,
    bool clearError = false,
  }) {
    return AuthState(
      stage: stage ?? this.stage,
      loading: loading ?? this.loading,
      error: clearError ? null : (error ?? this.error),
      mfaToken: mfaToken ?? this.mfaToken,
      totpEnrollmentRequired: totpEnrollmentRequired ?? this.totpEnrollmentRequired,
      enrollment: enrollment ?? this.enrollment,
      refreshToken: refreshToken ?? this.refreshToken,
      vinculos: vinculos ?? this.vinculos,
      papel: papel ?? this.papel,
      unidadeId: unidadeId ?? this.unidadeId,
    );
  }
}

class AuthController extends StateNotifier<AuthState> {
  final AuthRepository _repo;
  final TokenStorage _storage;
  AuthController(this._repo, this._storage) : super(const AuthState());

  /// Passo 1 — senha. Se for primeiro acesso, já obtém o enrollment do TOTP.
  Future<void> login(String email, String senha) async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      final res = await _repo.login(email, senha);
      TotpEnrollment? enroll;
      if (res.totpEnrollmentRequired) {
        enroll = await _repo.enrollTotp(res.mfaToken);
      }
      state = state.copyWith(
        stage: AuthStage.awaiting2fa,
        loading: false,
        mfaToken: res.mfaToken,
        totpEnrollmentRequired: res.totpEnrollmentRequired,
        enrollment: enroll,
      );
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  /// Passo 2 — código TOTP.
  Future<void> verify2fa(String codigo) async {
    if (state.mfaToken == null) return;
    state = state.copyWith(loading: true, clearError: true);
    try {
      final res = await _repo.verify2fa(state.mfaToken!, codigo);
      state = state.copyWith(
        stage: AuthStage.selectingContext,
        loading: false,
        refreshToken: res.refreshToken,
        vinculos: res.vinculos,
      );
      // Atalho: se houver um único vínculo, seleciona automaticamente.
      if (res.vinculos.length == 1) {
        final v = res.vinculos.first;
        await selectContext(v.unidadeId, v.papel);
      }
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  /// Passo 3 — escolhe unidade + papel e conclui a sessão.
  Future<void> selectContext(String unidadeId, String papel) async {
    if (state.refreshToken == null) return;
    state = state.copyWith(loading: true, clearError: true);
    try {
      final tokens = await _repo.selectContext(state.refreshToken!, unidadeId, papel);
      await _storage.save(access: tokens.accessToken, refresh: tokens.refreshToken);
      state = state.copyWith(
        stage: AuthStage.authenticated,
        loading: false,
        papel: tokens.papel,
        unidadeId: tokens.unidadeId,
      );
    } catch (e) {
      state = state.copyWith(loading: false, error: e.toString());
    }
  }

  /// Login por certificado digital (VIDaaS): o backend já validou a aprovação
  /// no app do PSC e devolveu refresh + vínculos (mesmo formato do 2FA).
  Future<void> adoptVidaasLogin(Verify2FAResult result) async {
    state = state.copyWith(
      stage: AuthStage.selectingContext,
      loading: false,
      clearError: true,
      refreshToken: result.refreshToken,
      vinculos: result.vinculos,
    );
    if (result.vinculos.length == 1) {
      final v = result.vinculos.first;
      await selectContext(v.unidadeId, v.papel);
    }
  }

  Future<void> logout() async {
    await _storage.clear();
    state = const AuthState();
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController(
    ref.watch(authRepositoryProvider),
    ref.watch(tokenStorageProvider),
  );
});
