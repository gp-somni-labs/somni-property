import 'package:flutter/foundation.dart';

/// OIDC Configuration for Authelia SSO
///
/// This configuration supports multiple environments:
/// - VPN (Tailscale): Uses internal auth.home.lan
/// - Public: Uses auth.somni-labs.tech
/// - Tailscale direct: Uses auth.tail58c8e4.ts.net
class OidcConfig {
  OidcConfig._();

  // Client Configuration
  static const String clientId = 'somni-property';

  // Authelia OIDC Endpoints (base URLs)
  static const String issuerVpn = 'https://auth.home.lan';
  static const String issuerPublic = 'https://auth.somni-labs.tech';
  static const String issuerTailscale = 'https://auth.tail58c8e4.ts.net';

  // Redirect URIs - Web/Desktop focused for property management
  static const String redirectUriWeb = 'https://property.home.lan/auth/callback';
  static const String redirectUriWebPublic = 'https://property.somni-labs.tech/auth/callback';
  static const String redirectUriDesktop = 'somniproperty://auth/callback';

  // Post-logout redirect
  static const String postLogoutRedirectWeb = 'https://property.home.lan';
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

  /// Get the appropriate issuer based on network status
  static String getIssuer({required bool isVpnConnected}) {
    if (isVpnConnected) {
      return issuerVpn;
    }
    return issuerPublic;
  }

  /// Get the appropriate redirect URI based on platform
  static String getRedirectUri() {
    if (kIsWeb) {
      // For web, use the web callback URL
      // In production, this should match the deployed URL
      return redirectUriWeb;
    }
    // Desktop uses custom URL scheme
    return redirectUriDesktop;
  }

  /// Get the post-logout redirect URI based on platform
  static String getPostLogoutRedirectUri() {
    if (kIsWeb) {
      return postLogoutRedirectWeb;
    }
    return postLogoutRedirectDesktop;
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
