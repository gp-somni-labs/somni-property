import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Initialize web-specific services
Future<void> initializePlatform() async {
  debugPrint('Initializing web platform...');

  // Web-specific initialization
  // No special setup needed for web

  debugPrint('Web platform initialized');
}

/// Get provider overrides for web
List<Override> getProviderOverrides() {
  return [];
}
