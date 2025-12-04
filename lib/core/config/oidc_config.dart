import 'package:flutter/foundation.dart';
import 'oidc_config_stub.dart' if (dart.library.html) 'oidc_config_web.dart';

/// Access zone enumeration for 3-zone networking
enum AccessZone {
  /// Local LAN access (home.lan)
  lan,
  /// Tailscale VPN access (tail58c8e4.ts.net)
  tailscale,
  /// Public internet access (somni-labs.tech)
  public,
}

/// OIDC Configuration for Authelia SSO
///
/// This configuration supports multiple environments (3-zone access):
/// - Zone 1 (LAN): Uses auth.home.lan / property.home.lan
/// - Zone 2 (Tailscale): Uses auth.tail58c8e4.ts.net / property.tail58c8e4.ts.net
/// - Zone 3 (Public): Uses auth.somni-labs.tech / property.somni-labs.tech
class OidcConfig {
  OidcConfig._();

  // Client Configuration
  static const String clientId = 'somni-property';

  // Domain mappings for each zone
  static const Map<AccessZone, String> _authDomains = {
    AccessZone.lan: 'auth.home.lan',
    AccessZone.tailscale: 'auth.tail58c8e4.ts.net',
    AccessZone.public: 'auth.somni-labs.tech',
  };

  static const Map<AccessZone, String> _appDomains = {
    AccessZone.lan: 'property.home.lan',
    AccessZone.tailscale: 'property.tail58c8e4.ts.net',
    AccessZone.public: 'property.somni-labs.tech',
  };

  // Authelia OIDC Endpoints (base URLs) - kept for backwards compatibility
  static const String issuerVpn = 'https://auth.home.lan';
  static const String issuerPublic = 'https://auth.somni-labs.tech';
  static const String issuerTailscale = 'https://auth.tail58c8e4.ts.net';

  // Redirect URIs - kept for backwards compatibility
  static const String redirectUriWebLan = 'https://property.home.lan/auth/callback';
  static const String redirectUriWebTailscale = 'https://property.tail58c8e4.ts.net/auth/callback';
  static const String redirectUriWebPublic = 'https://property.somni-labs.tech/auth/callback';
  static const String redirectUriDesktop = 'somniproperty://auth/callback';

  // Post-logout redirects
  static const String postLogoutRedirectDesktop = 'somniproperty://auth/logout';

  // Scopes requested from Authelia
  static const List<String> scopes = [
    'openid',
    'email',
    'profile',
    'groups',
    'offline_access', // For refresh tokens
  ];

  // PKCE Configuration
  static const bool usePkce = true;

  /// Cached access zone (determined once at startup)
  static AccessZone? _cachedZone;

  /// Detect the current access zone based on the browser's host
  static AccessZone detectAccessZone() {
    if (_cachedZone != null) return _cachedZone!;

    if (kIsWeb) {
      try {
        // Get the current host from the browser window
        final host = _getCurrentHost();
        debugPrint('OIDC: Detected host: $host');

        if (host.contains('home.lan')) {
          _cachedZone = AccessZone.lan;
        } else if (host.contains('ts.net') || host.contains('tailscale')) {
          _cachedZone = AccessZone.tailscale;
        } else if (host.contains('somni-labs.tech')) {
          _cachedZone = AccessZone.public;
        } else {
          // Default to public for unknown hosts (including localhost)
          debugPrint('OIDC: Unknown host "$host", defaulting to public zone');
          _cachedZone = AccessZone.public;
        }
      } catch (e) {
        debugPrint('OIDC: Error detecting zone: $e, defaulting to public');
        _cachedZone = AccessZone.public;
      }
    } else {
      // Desktop app - default to LAN (assume local network)
      _cachedZone = AccessZone.lan;
    }

    debugPrint('OIDC: Access zone detected: ${_cachedZone!.name}');
    return _cachedZone!;
  }

  /// Get the current host from the browser (web only)
  static String _getCurrentHost() {
    if (kIsWeb) {
      // Use conditional import to access window.location.host
      return getWebHost();
    }
    return '';
  }

  /// Get the issuer URL for the detected zone
  static String getIssuerForZone(AccessZone zone) {
    return 'https://${_authDomains[zone]}';
  }

  /// Get the redirect URI for the detected zone
  static String getRedirectUriForZone(AccessZone zone) {
    if (!kIsWeb) {
      return redirectUriDesktop;
    }
    return 'https://${_appDomains[zone]}/auth/callback';
  }

  /// Get the post-logout redirect URI for the detected zone
  static String getPostLogoutRedirectUriForZone(AccessZone zone) {
    if (!kIsWeb) {
      return postLogoutRedirectDesktop;
    }
    return 'https://${_appDomains[zone]}';
  }

  /// Get the appropriate issuer based on network status (backwards compatible)
  /// @deprecated Use getIssuerForZone with detectAccessZone() instead
  static String getIssuer({required bool isVpnConnected}) {
    // Use zone detection for more accurate results
    final zone = detectAccessZone();
    return getIssuerForZone(zone);
  }

  /// Get the appropriate redirect URI based on platform and current zone
  static String getRedirectUri() {
    if (!kIsWeb) {
      return redirectUriDesktop;
    }
    final zone = detectAccessZone();
    return getRedirectUriForZone(zone);
  }

  /// Get the post-logout redirect URI based on platform and current zone
  static String getPostLogoutRedirectUri() {
    if (!kIsWeb) {
      return postLogoutRedirectDesktop;
    }
    final zone = detectAccessZone();
    return getPostLogoutRedirectUriForZone(zone);
  }

  /// Build authorization endpoint
  static String authorizationEndpoint(String issuer) {
    return '$issuer/api/oidc/authorization';
  }

  /// Build token endpoint
  static String tokenEndpoint(String issuer) {
    return '$issuer/api/oidc/token';
  }

  /// Build userinfo endpoint
  static String userinfoEndpoint(String issuer) {
    return '$issuer/api/oidc/userinfo';
  }

  /// Build end session (logout) endpoint
  static String endSessionEndpoint(String issuer) {
    return '$issuer/api/oidc/logout';
  }

  /// Build JWKS URI for token verification
  static String jwksUri(String issuer) {
    return '$issuer/jwks.json';
  }

  /// Build discovery URL
  static String discoveryUrl(String issuer) {
    return '$issuer/.well-known/openid-configuration';
  }
}

/// LDAP Group to App Role mapping for Property Management
class OidcRoleMapper {
  OidcRoleMapper._();

  /// Map LDAP groups to application roles
  ///
  /// LDAP Groups (from Authelia):
  /// - admins: System administrators - full access
  /// - managers: Property managers - manage properties, tenants, leases
  /// - tenants: Tenants - view their own leases and submit maintenance requests
  static String mapGroupsToRole(List<String> groups) {
    // Priority order: admin > manager > tenant > viewer
    if (groups.contains('admins')) {
      return 'admin';
    }
    if (groups.contains('managers')) {
      return 'manager';
    }
    if (groups.contains('tenants')) {
      return 'tenant';
    }
    // Default role if no matching group - read-only viewer
    return 'viewer';
  }

  /// Check if user has required group for app access
  static bool hasAppAccess(List<String> groups) {
    const allowedGroups = ['managers', 'admins', 'tenants'];
    return groups.any((g) => allowedGroups.contains(g));
  }

  /// Check if user can manage properties
  static bool canManageProperties(List<String> groups) {
    return groups.contains('admins') || groups.contains('managers');
  }

  /// Check if user can manage tenants
  static bool canManageTenants(List<String> groups) {
    return groups.contains('admins') || groups.contains('managers');
  }

  /// Check if user can view financial data
  static bool canViewFinancials(List<String> groups) {
    return groups.contains('admins') || groups.contains('managers');
  }
}
