/// Application-wide constants for SomniProperty
class AppConstants {
  AppConstants._();

  static const String appName = 'SomniProperty';
  static const String appVersion = '1.0.0';

  // API Configuration - SomniProperty Backend
  // Tailscale VPN endpoint (primary) - MUST use HTTPS to avoid mixed content errors
  static const String tailscaleBaseUrl =
      'https://property.tail58c8e4.ts.net';
  // LAN endpoint (for on-site use)
  static const String localBaseUrl = 'https://property.home.lan';
  // Public endpoint (fallback)
  static const String publicBaseUrl = 'https://property.somni-labs.tech';

  // API Endpoints
  static const String apiVersion = '/api/v1';

  // Timeouts
  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);

  // Token Keys
  static const String accessTokenKey = 'access_token';
  static const String refreshTokenKey = 'refresh_token';
  static const String userIdKey = 'user_id';
  static const String userRoleKey = 'user_role';

  // Cache Duration
  static const Duration cacheValidDuration = Duration(hours: 1);

  // Property Statuses
  static const List<String> propertyStatuses = [
    'active',
    'inactive',
    'maintenance',
    'renovation',
  ];

  // Unit Statuses
  static const List<String> unitStatuses = [
    'available',
    'occupied',
    'maintenance',
    'reserved',
  ];

  // Lease Statuses
  static const List<String> leaseStatuses = [
    'draft',
    'pending',
    'active',
    'expired',
    'terminated',
  ];

  // Maintenance Request Statuses
  static const List<String> maintenanceStatuses = [
    'open',
    'assigned',
    'in_progress',
    'completed',
    'cancelled',
  ];

  // Priority Levels
  static const List<String> priorityLevels = [
    'low',
    'normal',
    'high',
    'emergency',
  ];

  // Property Types
  static const List<String> propertyTypes = [
    'single_family',
    'multi_family',
    'apartment',
    'condo',
    'townhouse',
    'commercial',
  ];
}

/// MinIO/S3 Configuration
class MinioConstants {
  MinioConstants._();

  // Internal cluster endpoint
  static const String endpoint = 'minio.storage.svc.cluster.local';
  // Tailscale VPN endpoint - MUST use HTTPS to avoid mixed content errors
  static const String tailscaleEndpoint = 'minio.tail58c8e4.ts.net';
  // LAN endpoint
  static const String lanEndpoint = 'minio.home.lan';
  static const int port = 9000;
  static const bool useSSL = true;

  // Buckets
  static const String propertyMediaBucket = 'property-media';
  static const String documentsBucket = 'documents';
  static const String leaseDocumentsBucket = 'lease-documents';
}
