import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:somni_property/core/config/oidc_config.dart';

/// Helper function to pump a widget with Riverpod provider scope
Future<void> pumpApp(
  WidgetTester tester,
  Widget widget, {
  List<Override> overrides = const [],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        home: Scaffold(body: widget),
      ),
    ),
  );
}

/// Helper function to pump a widget with custom providers
Future<void> pumpWidgetWithProviders(
  WidgetTester tester,
  Widget widget, {
  List<Override> overrides = const [],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: widget,
    ),
  );
}

/// Helper to wait for async operations
Future<void> pumpAndSettle(WidgetTester tester) async {
  await tester.pump();
  await tester.pumpAndSettle();
}

/// Helper to find text in widget tree
Finder findTextContaining(String text) {
  return find.byWidgetPredicate(
    (widget) => widget is Text && widget.data?.contains(text) == true,
  );
}

/// Mock OIDC configuration for tests
class MockOidcConfig implements OidcConfig {
  @override
  String get discoveryUrl => 'https://auth.test.com/.well-known/openid-configuration';

  @override
  String get clientId => 'test-client-id';

  @override
  String get redirectUrl => 'com.somni.property://callback';

  @override
  List<String> get scopes => ['openid', 'profile', 'email'];
}
