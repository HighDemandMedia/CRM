import 'auth_service.dart';

/// Local build: external crash reporting and identity sharing are disabled.
class CrashReporting {
  static Future<void> applyFromAuth(AuthService auth) async {}
  static Future<void> clear() async {}
}
