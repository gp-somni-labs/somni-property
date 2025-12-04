import 'package:flutter/foundation.dart' show kIsWeb;

import 'platform_stub.dart' if (dart.library.io) 'platform_io.dart';

/// Utility class for platform detection
class PlatformUtils {
  PlatformUtils._();

  /// Check if running on web
  static bool get isWeb => kIsWeb;

  /// Check if running on mobile (iOS or Android)
  static bool get isMobile {
    if (kIsWeb) return false;
    return Platform.isIOS || Platform.isAndroid;
  }

  /// Check if running on desktop (macOS, Windows, or Linux)
  static bool get isDesktop {
    if (kIsWeb) return false;
    return Platform.isMacOS || Platform.isWindows || Platform.isLinux;
  }

  /// Check if running on iOS
  static bool get isIOS {
    if (kIsWeb) return false;
    return Platform.isIOS;
  }

  /// Check if running on Android
  static bool get isAndroid {
    if (kIsWeb) return false;
    return Platform.isAndroid;
  }

  /// Check if running on macOS
  static bool get isMacOS {
    if (kIsWeb) return false;
    return Platform.isMacOS;
  }

  /// Check if running on Windows
  static bool get isWindows {
    if (kIsWeb) return false;
    return Platform.isWindows;
  }

  /// Check if running on Linux
  static bool get isLinux {
    if (kIsWeb) return false;
    return Platform.isLinux;
  }

  /// Check if file system access is supported
  static bool get supportsFileSystem => !isWeb;

  /// Get current platform name
  static String get platformName {
    if (kIsWeb) return 'Web';
    if (Platform.isIOS) return 'iOS';
    if (Platform.isAndroid) return 'Android';
    if (Platform.isMacOS) return 'macOS';
    if (Platform.isWindows) return 'Windows';
    if (Platform.isLinux) return 'Linux';
    return 'Unknown';
  }
}

/// Platform type enum
enum AppPlatform {
  ios,
  android,
  web,
  macos,
  windows,
  linux,
}

extension AppPlatformExtension on AppPlatform {
  bool get isMobile => this == AppPlatform.ios || this == AppPlatform.android;
  bool get isDesktop =>
      this == AppPlatform.macos ||
      this == AppPlatform.windows ||
      this == AppPlatform.linux;
  bool get isWeb => this == AppPlatform.web;
}

/// Get current app platform
AppPlatform get currentPlatform {
  if (kIsWeb) return AppPlatform.web;
  if (Platform.isIOS) return AppPlatform.ios;
  if (Platform.isAndroid) return AppPlatform.android;
  if (Platform.isMacOS) return AppPlatform.macos;
  if (Platform.isWindows) return AppPlatform.windows;
  if (Platform.isLinux) return AppPlatform.linux;
  return AppPlatform.web; // Fallback
}
