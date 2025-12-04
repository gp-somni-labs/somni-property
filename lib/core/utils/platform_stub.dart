/// Stub platform class for web
class Platform {
  Platform._();

  static bool get isIOS => false;
  static bool get isAndroid => false;
  static bool get isMacOS => false;
  static bool get isWindows => false;
  static bool get isLinux => false;
  static bool get isFuchsia => false;
  static String get operatingSystem => 'web';
  static String get operatingSystemVersion => '';
  static String get localHostname => 'localhost';
  static int get numberOfProcessors => 1;
  static String get pathSeparator => '/';
  static String get localeName => 'en_US';
}
