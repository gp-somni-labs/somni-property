// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

/// Get the current host from the browser window (web implementation)
String getWebHost() {
  return html.window.location.host;
}
