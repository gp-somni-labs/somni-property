// Stub implementation for web platform
// DNS lookup is not available on web

Future<bool> dnsLookup(String host) async {
  // DNS lookup not available on web
  return false;
}

Future<bool> checkInternetConnectivity() async {
  // Assume connected on web (browser handles offline state)
  return true;
}
