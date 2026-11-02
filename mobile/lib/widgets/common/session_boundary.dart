import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../services/auth_service.dart';

/// A session owns its entire provider container and navigation tree.
/// Rebuilding providers alone can retain AsyncValue.previous and notifier fields.
class SessionBoundary extends StatelessWidget {
  const SessionBoundary({required this.child, super.key});
  final Widget child;

  @override
  Widget build(BuildContext context) => ValueListenableBuilder<int>(
    valueListenable: AuthService().sessionChanges,
    builder: (context, generation, _) =>
        ProviderScope(key: ValueKey(generation), child: child),
  );
}
