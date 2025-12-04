import 'dart:io';

/// Platform-specific implementation for native platforms (iOS, Android, desktop)
/// Uses dart:io for DNS lookup

Future<bool> dnsLookup(String host) async {
  try {
    final result =
        await InternetAddress.lookup(host).timeout(const Duration(seconds: 3));
    return result.isNotEmpty && result[0].rawAddress.isNotEmpty;
  } catch (_) {
    return false;
  }
}

Future<bool> checkInternetConnectivity() async {
  try {
    final result = await InternetAddress.lookup('google.com')
        .timeout(const Duration(seconds: 3));
    return result.isNotEmpty && result[0].rawAddress.isNotEmpty;
  } catch (_) {
    return false;
  }
}
