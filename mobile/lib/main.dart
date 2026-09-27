import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/theme.dart';
import 'routes/app_router.dart';
import 'services/auth_service.dart';
import 'services/crash_reporting.dart';

void main() async {
  runZonedGuarded<Future<void>>(
    () async {
      WidgetsFlutterBinding.ensureInitialized();

      await AuthService().initialize();
      // Tag any already-signed-in session so the first uncaught error has a user.
      await CrashReporting.applyFromAuth(AuthService());

      SystemChrome.setSystemUIOverlayStyle(
        const SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.dark,
          systemNavigationBarColor: AppColors.surface,
          systemNavigationBarIconBrightness: Brightness.dark,
        ),
      );

      SystemChrome.setPreferredOrientations([
        DeviceOrientation.portraitUp,
        DeviceOrientation.portraitDown,
      ]);

      runApp(const ProviderScope(child: HighDemandMediaApp()));
    },
    (error, stack) {
      // Catch-all for anything that escaped the zone, e.g. errors from
      // microtasks scheduled before PlatformDispatcher.onError was wired.
      debugPrint('Application error: $error');
    },
  );
}

/// BottleCRM - Main Application Widget
class HighDemandMediaApp extends ConsumerWidget {
  const HighDemandMediaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: 'High Demand Media CRM',
      debugShowCheckedModeBanner: false,

      // Theme
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.light,

      // Router
      routerConfig: router,

      // Scroll behavior for smooth scrolling
      scrollBehavior: const MaterialScrollBehavior().copyWith(
        physics: const BouncingScrollPhysics(),
      ),
    );
  }
}
