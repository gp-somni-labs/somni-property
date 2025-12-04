import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Service locator for shared services
class ServiceLocator {
  ServiceLocator._();

  static bool _initialized = false;

  /// Initialize all services
  static Future<void> init() async {
    if (_initialized) {
      debugPrint('ServiceLocator already initialized');
      return;
    }

    debugPrint('Initializing ServiceLocator...');

    // Initialize core services
    // Add service initialization here as needed

    _initialized = true;
    debugPrint('ServiceLocator initialized');
  }

  /// Reset all services (for testing)
  static Future<void> reset() async {
    _initialized = false;
  }
}

/// Get provider overrides (from platform-specific files)
List<Override> getProviderOverrides() {
  return [];
}
