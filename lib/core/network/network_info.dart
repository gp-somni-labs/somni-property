import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/constants/app_constants.dart';

// Conditional import for dart:io (not available on web)
import 'network_info_stub.dart' if (dart.library.io) 'network_info_io.dart'
    as platform;

/// Connectivity result for compatibility
enum ConnectivityStatus {
  online,
  offline,
}

/// Provider for network info
final networkInfoProvider = Provider<NetworkInfo>((ref) {
  return NetworkInfoImpl();
});

/// Provider for VPN connection status - auto-refresh every 30 seconds
final vpnStatusProvider = FutureProvider.autoDispose<bool>((ref) async {
  final networkInfo = ref.watch(networkInfoProvider);
  final result = await networkInfo.isVpnConnected;

  // Auto-refresh after 30 seconds
  ref.keepAlive();
  Future.delayed(const Duration(seconds: 30), () {
    ref.invalidateSelf();
  });

  return result;
});

/// Provider for overall connectivity status
final connectivityProvider = StreamProvider<ConnectivityStatus>((ref) {
  // Simple connectivity stream for web
  return Stream.value(ConnectivityStatus.online);
});

/// Abstract network info interface
abstract class NetworkInfo {
  Future<bool> get isConnected;
  Future<bool> get isVpnConnected;
  Future<String> get currentBaseUrl;
  Stream<ConnectivityStatus> get connectivityStream;
}

/// Implementation of network info with actual VPN detection
class NetworkInfoImpl implements NetworkInfo {
  NetworkInfoImpl();

  // Cache VPN status to avoid excessive network calls
  bool? _cachedVpnStatus;
  DateTime? _lastVpnCheck;
  static const _vpnCheckCacheDuration = Duration(seconds: 15);

  // Dio instance for connectivity checks
  late final Dio _dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 5),
    receiveTimeout: const Duration(seconds: 5),
  ));

  @override
  Future<bool> get isConnected async {
    // Use platform-specific implementation
    return platform.checkInternetConnectivity();
  }

  @override
  Future<bool> get isVpnConnected async {
    // On web, skip VPN check entirely - zone is detected from browser URL
    // This avoids mixed content errors and unnecessary network requests
    if (kIsWeb) {
      debugPrint('VPN status: skipped on web (zone detected from URL)');
      return false;
    }

    // Check cache first
    if (_cachedVpnStatus != null && _lastVpnCheck != null) {
      final elapsed = DateTime.now().difference(_lastVpnCheck!);
      if (elapsed < _vpnCheckCacheDuration) {
        debugPrint('VPN status (cached): $_cachedVpnStatus');
        return _cachedVpnStatus!;
      }
    }

    // Perform actual VPN check by trying to reach the Tailscale endpoint
    final isConnected = await _checkTailscaleConnectivity();

    // Update cache
    _cachedVpnStatus = isConnected;
    _lastVpnCheck = DateTime.now();

    debugPrint('VPN status (fresh check): $isConnected');
    return isConnected;
  }

  /// Check if we can reach the Tailscale endpoint
  Future<bool> _checkTailscaleConnectivity() async {
    // On web, try a fetch to the Tailscale endpoint
    // On native platforms, try DNS lookup first, then HTTP

    final tailscaleHost = AppConstants.tailscaleBaseUrl
        .replaceAll('https://', '')
        .replaceAll('http://', '')
        .split('/')[0];

    debugPrint('Checking Tailscale connectivity to: $tailscaleHost');

    if (kIsWeb) {
      // On web, try HTTP request
      return _checkHttpConnectivity(AppConstants.tailscaleBaseUrl);
    }

    // On native platforms, try DNS lookup first (faster)
    final dnsSuccess = await platform.dnsLookup(tailscaleHost);
    if (dnsSuccess) {
      debugPrint('Tailscale DNS lookup successful');
      // DNS resolved, now verify HTTP connectivity
      return _checkHttpConnectivity(AppConstants.tailscaleBaseUrl);
    } else {
      debugPrint('Tailscale DNS lookup failed');
    }

    return false;
  }

  /// Check HTTP connectivity to an endpoint
  Future<bool> _checkHttpConnectivity(String url) async {
    try {
      // Try to reach a health endpoint or just the base URL
      // Using HEAD request for minimal data transfer
      final response = await _dio.head(
        '$url/health',
        options: Options(
          validateStatus: (status) => status != null && status < 500,
        ),
      );

      debugPrint('HTTP check to $url: ${response.statusCode}');
      return response.statusCode != null && response.statusCode! < 500;
    } catch (e) {
      // If /health doesn't exist, try the base URL
      try {
        final response = await _dio.head(
          url,
          options: Options(
            validateStatus: (status) => status != null && status < 500,
          ),
        );
        debugPrint('HTTP check to $url (base): ${response.statusCode}');
        return response.statusCode != null && response.statusCode! < 500;
      } catch (e2) {
        debugPrint('HTTP connectivity check failed: $e2');
        return false;
      }
    }
  }

  @override
  Future<String> get currentBaseUrl async {
    // Check VPN first
    if (await isVpnConnected) {
      debugPrint('Using Tailscale URL: ${AppConstants.tailscaleBaseUrl}');
      return AppConstants.tailscaleBaseUrl;
    }

    // Fall back to public URL
    debugPrint('Using public URL: ${AppConstants.publicBaseUrl}');
    return AppConstants.publicBaseUrl;
  }

  @override
  Stream<ConnectivityStatus> get connectivityStream =>
      Stream.value(ConnectivityStatus.online);

  /// Force refresh VPN status (clears cache)
  void invalidateVpnCache() {
    _cachedVpnStatus = null;
    _lastVpnCheck = null;
  }
}

/// VPN Status enum
enum VpnStatus {
  connected,
  disconnected,
  connecting,
  error,
}

/// Extension for VpnStatus
extension VpnStatusExtension on VpnStatus {
  String get displayName {
    switch (this) {
      case VpnStatus.connected:
        return 'Connected';
      case VpnStatus.disconnected:
        return 'Disconnected';
      case VpnStatus.connecting:
        return 'Connecting...';
      case VpnStatus.error:
        return 'Error';
    }
  }

  bool get isConnected => this == VpnStatus.connected;
}
