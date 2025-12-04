import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// Initialize desktop-specific services
Future<void> initializePlatform() async {
  debugPrint('Initializing desktop platform...');

  // Initialize sqflite for desktop
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  debugPrint('Desktop platform initialized');
}

/// Get provider overrides for desktop
List<Override> getProviderOverrides() {
  return [];
}
