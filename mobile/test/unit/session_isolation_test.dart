import 'dart:async';
import 'dart:convert';

import 'package:bottle_crm/config/api_config.dart';
import 'package:bottle_crm/data/models/auth_response.dart';
import 'package:bottle_crm/providers/contacts_provider.dart';
import 'package:bottle_crm/providers/settings_provider.dart';
import 'package:bottle_crm/services/api_service.dart';
import 'package:bottle_crm/services/auth_service.dart';
import 'package:bottle_crm/services/token_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/material.dart';
import 'package:bottle_crm/screens/tickets/tickets_list_screen.dart';
import 'package:bottle_crm/widgets/common/session_boundary.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DelayedStorage extends TokenStorage {
  final entered = Completer<void>();
  final release = Completer<void>();
  bool delay = false;
  @override
  Future<void> write({String? access, String? refresh}) async {
    if (delay) {
      delay = false;
      entered.complete();
      await release.future;
    }
    await super.write(access: access, refresh: refresh);
  }
}

Map<String, Object> loginPayload(String id) => {
  'access_token': 'access-$id',
  'refresh_token': 'refresh-$id',
  'user': {'id': id, 'email': '$id@example.test'},
  'organizations': [
    {'id': 'org-$id', 'name': id},
  ],
  'current_org': {'id': 'org-$id', 'name': id},
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late ApiService api;
  late AuthService auth;
  setUp(() async {
    api = ApiService();
    auth = AuthService();
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
    auth.setTokenStorageForTesting(TokenStorage());
    api.setClientForTesting(MockClient((_) async => http.Response('{}', 200)));
    await auth.signOut();
    api.setRefreshCallback(null);
  });
  tearDown(() async {
    api.setClientForTesting(MockClient((_) async => http.Response('{}', 200)));
    await auth.signOut();
    auth.setTokenStorageForTesting(TokenStorage());
  });

  Future<void> login(String id) async {
    api.setClientForTesting(
      MockClient((_) async => http.Response(jsonEncode(loginPayload(id)), 200)),
    );
    expect(
      await auth.signInWithMagicCode(email: '$id@example.test', code: '123456'),
      isTrue,
    );
  }

  test('late refresh cannot restore a logged-out session', () async {
    await login('old');
    final response = Completer<http.Response>();
    final entered = Completer<void>();
    api.setClientForTesting(
      MockClient((request) {
        if (request.url.toString() == ApiConfig.refreshToken) {
          entered.complete();
          return response.future;
        }
        return Future.value(http.Response('{}', 200));
      }),
    );
    final pending = auth.refreshAccessToken();
    await entered.future;
    await auth.signOut();
    response.complete(
      http.Response('{"access":"late","refresh":"late-refresh"}', 200),
    );
    expect(await pending, isFalse);
    expect(auth.accessToken, isNull);
    expect((await TokenStorage().read()).refresh, isNull);
  });

  test('late refresh cannot replace a new user', () async {
    await login('old');
    final response = Completer<http.Response>();
    api.setClientForTesting(MockClient((_) => response.future));
    final pending = auth.refreshAccessToken();
    await login('new');
    response.complete(
      http.Response('{"access":"old-late","refresh":"old-late"}', 200),
    );
    expect(await pending, isFalse);
    expect(auth.currentUser?.id, 'new');
    expect((await TokenStorage().read()).access, 'access-new');
  });

  test('an in-flight secure-storage write cannot outlive logout', () async {
    await login('old');
    final storage = DelayedStorage()..delay = true;
    auth.setTokenStorageForTesting(storage);
    api.setClientForTesting(
      MockClient(
        (_) async =>
            http.Response('{"access":"renewed","refresh":"renewed"}', 200),
      ),
    );
    final pending = auth.refreshAccessToken();
    await storage.entered.future;
    final logout = auth.signOut();
    expect(auth.accessToken, isNull);
    storage.release.complete();
    await logout;
    expect(await pending, isFalse);
    expect((await TokenStorage().read()).access, isNull);
  });

  test(
    'old API response cannot retry with the next organization token',
    () async {
      api.setAccessToken('old');
      api.setOrganizationId('old-org');
      final response = Completer<http.Response>();
      var sends = 0;
      var refreshes = 0;
      api.setRefreshCallback(() async {
        refreshes++;
        return true;
      });
      api.setClientForTesting(
        MockClient((_) {
          sends++;
          return response.future;
        }),
      );
      final pending = api.get(ApiConfig.contacts);
      api.setOrganizationId('new-org');
      api.setAccessToken('new');
      response.complete(http.Response('{}', 401));
      expect((await pending).success, isFalse);
      expect(sends, 1);
      expect(refreshes, 0);
    },
  );

  testWidgets('saved ticket filters stay with their user and organization', (
    tester,
  ) async {
    await tester.runAsync(() => login('old'));
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      'tickets_filters_v1',
      '{"search":"Legacy private search"}',
    );
    await prefs.setString(
      'tickets_filters_v2:old:org-old',
      '{"search":"Private search"}',
    );
    void mockLists() => api.setClientForTesting(
      MockClient((_) async => http.Response('{"results":[],"count":0}', 200)),
    );
    mockLists();
    await tester.pumpWidget(
      const SessionBoundary(child: MaterialApp(home: TicketsListScreen())),
    );
    await tester.pumpAndSettle();
    expect(find.text('Private search'), findsOneWidget);
    expect(prefs.containsKey('tickets_filters_v1'), isFalse);
    await tester.runAsync(() => login('new'));
    mockLists();
    await tester.pumpAndSettle();
    expect(find.text('Private search'), findsNothing);
    expect(find.text('Legacy private search'), findsNothing);
    expect(
      prefs.getString('tickets_filters_v2:old:org-old'),
      contains('Private search'),
    );
    await tester.runAsync(() => login('old'));
    mockLists();
    await tester.pumpAndSettle();
    expect(find.text('Private search'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('session boundary replaces all provider and screen state', (
    tester,
  ) async {
    await tester.runAsync(() => login('old'));
    api.setClientForTesting(
      MockClient((request) async {
        if (request.url.toString() == ApiConfig.switchOrg) {
          return http.Response(
            '{"access_token":"new","refresh_token":"new"}',
            200,
          );
        }
        return http.Response('{"results":[],"count":0}', 200);
      }),
    );
    late ProviderContainer container;
    var screenMounts = 0;
    var screenDisposals = 0;
    await tester.pumpWidget(
      SessionBoundary(
        child: Consumer(
          builder: (context, ref, _) {
            container = ProviderScope.containerOf(context);
            return LifecycleProbe(
              onMount: () => screenMounts++,
              onDispose: () => screenDisposals++,
            );
          },
        ),
      ),
    );
    final oldContainer = container;
    final contacts = container.read(contactsProvider.notifier);
    final settings = container.read(customFieldsProvider.notifier);
    await tester.runAsync(() async {
      await container.read(contactsProvider.future);
      await container.read(customFieldsProvider.future);
      expect(
        await auth.selectOrganization(
          const Organization(id: 'next', name: 'Next'),
        ),
        isTrue,
      );
    });
    await tester.pump();
    expect(identical(oldContainer, container), isFalse);
    expect(
      identical(contacts, container.read(contactsProvider.notifier)),
      isFalse,
    );
    expect(
      identical(settings, container.read(customFieldsProvider.notifier)),
      isFalse,
    );
    expect(screenMounts, 2);
    expect(screenDisposals, 1);
    await tester.runAsync(() async {
      await container.read(contactsProvider.future);
      await container.read(customFieldsProvider.future);
    });
    await tester.pumpWidget(const SizedBox());
  });
}

class LifecycleProbe extends StatefulWidget {
  const LifecycleProbe({
    required this.onMount,
    required this.onDispose,
    super.key,
  });
  final VoidCallback onMount;
  final VoidCallback onDispose;
  @override
  State<LifecycleProbe> createState() => _LifecycleProbeState();
}

class _LifecycleProbeState extends State<LifecycleProbe> {
  @override
  void initState() {
    super.initState();
    widget.onMount();
  }

  @override
  void dispose() {
    widget.onDispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => const SizedBox();
}
