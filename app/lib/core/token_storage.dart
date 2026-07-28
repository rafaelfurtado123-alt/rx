import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Armazenamento seguro dos tokens (access/refresh) e do contexto ativo.
///
/// Usa `flutter_secure_storage` (Keychain/Keystore). Nunca persistir tokens em
/// SharedPreferences ou em disco não cifrado.
class TokenStorage {
  final FlutterSecureStorage _s;
  TokenStorage([FlutterSecureStorage? storage])
      : _s = storage ?? const FlutterSecureStorage();

  static const _kAccess = 'nefron.access';
  static const _kRefresh = 'nefron.refresh';

  Future<void> save({required String access, required String refresh}) async {
    await _s.write(key: _kAccess, value: access);
    await _s.write(key: _kRefresh, value: refresh);
  }

  Future<String?> get accessToken => _s.read(key: _kAccess);
  Future<String?> get refreshToken => _s.read(key: _kRefresh);

  Future<void> clear() async {
    await _s.delete(key: _kAccess);
    await _s.delete(key: _kRefresh);
  }
}
