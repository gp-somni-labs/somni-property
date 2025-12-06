# Flutter API Integration Guide

> **Date**: December 5, 2025
> **Status**: Properties Module Integrated
> **Backend**: `https://somniproperty.home.lan/api/v1`
> **Flutter App**: `/home/curiosity/.../somni-property/`

---

## Overview

This guide documents the integration between the SomniProperty Flutter app and the production backend API. The backend provides **553 HTTP endpoints** across multiple features, and this integration connects the Flutter app to these live endpoints.

---

## Architecture

### Network Layer

The Flutter app uses a clean architecture with:

1. **API Client** (`lib/core/network/api_client.dart`)
   - Dio-based HTTP client
   - JWT token management (access + refresh)
   - Automatic token refresh on 401 errors
   - Network-aware URL switching (LAN, VPN, Public)
   - Request/response logging

2. **Data Sources**
   - **Local**: Mock data for development (`property_local_datasource.dart`)
   - **Remote**: Production API calls (`property_remote_datasource.dart`)

3. **Repository Pattern**
   - Single repository with dual datasource support
   - Feature flag to switch between mock and real API
   - Consistent error handling across both modes

---

## Environment Configuration

### Base URLs

The app supports three network zones:

```dart
// lib/core/constants/app_constants.dart

// 1. LAN (on-site, primary for development)
static const String localBaseUrl = 'https://somniproperty.home.lan';

// 2. Tailscale VPN (secure remote access)
static const String tailscaleBaseUrl = 'https://property.tail58c8e4.ts.net';

// 3. Public (Cloudflare Tunnel)
static const String publicBaseUrl = 'https://property.somni-labs.tech';
```

### Automatic URL Selection

The `NetworkInfo` service automatically detects VPN connectivity and selects the appropriate base URL:

```dart
// lib/core/network/network_info.dart

@override
Future<String> get currentBaseUrl async {
  // Check VPN first
  if (await isVpnConnected) {
    return AppConstants.tailscaleBaseUrl;
  }

  // Fall back to public URL
  return AppConstants.publicBaseUrl;
}
```

**Note**: For web builds, VPN detection is skipped and the zone is determined from the browser URL.

---

## Authentication Flow

### 1. Login

The backend supports both traditional username/password and OIDC/SSO via Authelia:

```dart
// Traditional Login (POST /api/v1/auth/login)
final response = await apiClient.dio.post(
  '/auth/login',
  data: {
    'username': credentials.username,
    'password': credentials.password,
    'totp_code': credentials.totpCode, // Optional 2FA
  },
);

// Returns: { access_token, refresh_token, user: {...} }
```

### 2. Token Storage

Tokens are stored securely using `flutter_secure_storage`:

```dart
await apiClient.storeTokens(
  accessToken: response.data['access_token'],
  refreshToken: response.data['refresh_token'],
);
```

### 3. Authenticated Requests

The `_AuthInterceptor` automatically adds the Bearer token to all requests:

```dart
@override
Future<void> onRequest(
  RequestOptions options,
  RequestInterceptorHandler handler,
) async {
  final token = await apiClient.getAccessToken();
  if (token != null) {
    options.headers['Authorization'] = 'Bearer $token';
  }
  return handler.next(options);
}
```

### 4. Token Refresh

On 401 errors, the interceptor automatically refreshes the token:

```dart
@override
Future<void> onError(
  DioException err,
  ErrorInterceptorHandler handler,
) async {
  if (err.response?.statusCode == 401) {
    try {
      final newToken = await apiClient.refreshAccessToken();

      // Retry original request with new token
      final options = err.requestOptions;
      options.headers['Authorization'] = 'Bearer $newToken';

      final response = await apiClient.dio.fetch(options);
      return handler.resolve(response);
    } on TokenExpiredException {
      // Token refresh failed, need to re-login
      return handler.reject(err);
    }
  }
  return handler.next(err);
}
```

---

## Properties Module Integration

### Status: ✅ COMPLETE

The Properties module is fully integrated with the production backend.

### Files Changed

1. **Created**: `lib/features/properties/data/datasources/property_remote_datasource.dart`
   - Connects to backend `/api/v1/properties` endpoints
   - Implements GET list, GET detail, POST create, PUT update, DELETE
   - Handles pagination and filtering

2. **Updated**: `lib/features/properties/data/repositories/property_repository_impl.dart`
   - Added remote datasource support
   - Feature flag to switch between mock and real API
   - Consistent error handling

3. **Updated**: `lib/features/properties/presentation/providers/property_provider.dart`
   - Wired up remote datasource provider
   - Set `_useRemoteApi = true` for production

4. **Updated**: `lib/core/constants/app_constants.dart`
   - Fixed base URL to `https://somniproperty.home.lan`

### API Endpoints

| Method | Endpoint | Status | Notes |
|--------|----------|--------|-------|
| GET | `/properties` | ✅ Implemented | Supports pagination, search, filters |
| GET | `/properties/{id}` | ✅ Implemented | Fetch single property |
| POST | `/properties` | ✅ Implemented | Create new property |
| PUT | `/properties/{id}` | ✅ Implemented | Update property |
| DELETE | `/properties/{id}` | ✅ Implemented | Delete property |

### Request/Response Examples

#### GET /properties (List)

**Request**:
```http
GET /api/v1/properties?page=1&page_size=50&search=Austin&status=active
Authorization: Bearer <token>
```

**Response**:
```json
{
  "items": [
    {
      "id": "prop-001",
      "name": "Sunset Apartments",
      "address": "123 Main Street",
      "city": "Austin",
      "state": "TX",
      "zip_code": "78701",
      "type": "apartment",
      "status": "active",
      "total_units": 24,
      "occupied_units": 22,
      "monthly_revenue": 28600.0,
      "description": "Modern apartment complex...",
      "timezone": "America/Chicago",
      "owner_id": "admin",
      "manager_id": "manager-001",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-12-01T14:22:00Z"
    }
  ],
  "total": 6,
  "page": 1,
  "page_size": 50
}
```

#### POST /properties (Create)

**Request**:
```http
POST /api/v1/properties
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "New Property",
  "address": "456 Oak Lane",
  "city": "Austin",
  "state": "TX",
  "zip_code": "78704",
  "type": "apartment",
  "total_units": 12,
  "description": "New apartment building",
  "owner_id": "admin"
}
```

**Response**: Full property object with generated ID and timestamps.

### Schema Compatibility

**Flutter Model** ↔ **Backend Schema**:

| Flutter Field | Backend Field | Type | Notes |
|---------------|---------------|------|-------|
| `id` | `id` | String | UUID |
| `name` | `name` | String | Required |
| `address` | `address` | String | Required |
| `city` | `city` | String | Required |
| `state` | `state` | String | Required |
| `zipCode` | `zip_code` | String | Required |
| `type` | `type` | Enum | single_family, apartment, etc. |
| `status` | `status` | Enum | active, inactive, maintenance |
| `totalUnits` | `total_units` | int | Default 1 |
| `occupiedUnits` | `occupied_units` | int | Default 0 |
| `monthlyRevenue` | `monthly_revenue` | double? | Optional |
| `description` | `description` | String? | Optional |
| `imageUrl` | `image_url` | String? | Optional |
| `ownerId` | `owner_id` | String | Required |
| `managerId` | `manager_id` | String? | Optional |
| `createdAt` | `created_at` | DateTime | ISO 8601 |
| `updatedAt` | `updated_at` | DateTime | ISO 8601 |
| ❌ Missing | `timezone` | String | **TODO**: Add to Flutter model |

### Known Issues

1. **Missing `timezone` field**: Backend includes a `timezone` field (e.g., "America/Chicago") that Flutter model doesn't have. This is non-critical but should be added for completeness.

---

## Other Modules (Pending Integration)

The backend provides additional endpoints that need Flutter integration:

### Tenants Module

- **Endpoints**: 7
- **Status**: Data models exist, needs remote datasource
- **Files to update**:
  - Create `lib/features/tenants/data/datasources/tenant_remote_datasource.dart`
  - Update `lib/features/tenants/data/repositories/tenant_repository_impl.dart`

### Leases Module

- **Endpoints**: 9
- **Status**: Data models exist, needs remote datasource
- **Files to update**:
  - Create `lib/features/leases/data/datasources/lease_remote_datasource.dart`
  - Update `lib/features/leases/data/repositories/lease_repository_impl.dart`

### Payments Module

- **Endpoints**: 10+ (including Stripe integration)
- **Status**: Data models exist, needs remote datasource
- **Files to update**:
  - Create `lib/features/payments/data/datasources/payment_remote_datasource.dart`
  - Update `lib/features/payments/data/repositories/payment_repository_impl.dart`

### Work Orders Module

- **Endpoints**: 15+ (including tasks, materials, events)
- **Status**: Data models exist, needs remote datasource
- **Files to update**:
  - Create `lib/features/work_orders/data/datasources/work_order_remote_datasource.dart`
  - Update `lib/features/work_orders/data/repositories/work_order_repository_impl.dart`

---

## Testing Strategy

### 1. Unit Tests

Test API client, datasources, and repositories:

```dart
// test/features/properties/data/datasources/property_remote_datasource_test.dart

void main() {
  late PropertyRemoteDataSourceImpl datasource;
  late MockApiClient mockApiClient;

  setUp(() {
    mockApiClient = MockApiClient();
    datasource = PropertyRemoteDataSourceImpl(apiClient: mockApiClient);
  });

  group('getProperties', () {
    test('should return list of properties on success', () async {
      // Arrange
      final mockResponse = {
        'items': [
          {'id': 'prop-1', 'name': 'Test Property', ...}
        ],
        'total': 1,
        'page': 1,
        'page_size': 50,
      };

      when(mockApiClient.dio.get(any, queryParameters: anyNamed('queryParameters')))
          .thenAnswer((_) async => Response(data: mockResponse, statusCode: 200));

      // Act
      final result = await datasource.getProperties();

      // Assert
      expect(result, isA<List<PropertyModel>>());
      expect(result.length, 1);
    });
  });
}
```

### 2. Integration Tests

Test full flow from UI to API:

```dart
// integration_test/properties_test.dart

void main() {
  testWidgets('Properties list loads from API', (tester) async {
    // Launch app
    app.main();
    await tester.pumpAndSettle();

    // Navigate to properties
    await tester.tap(find.text('Properties'));
    await tester.pumpAndSettle();

    // Verify properties loaded from API
    expect(find.byType(PropertyCard), findsWidgets);
  });
}
```

### 3. Manual Testing Checklist

- [ ] Start app and verify network detection logs
- [ ] Login with test credentials
- [ ] Navigate to Properties list
- [ ] Verify properties load from backend
- [ ] Test search functionality
- [ ] Test filter by type/status
- [ ] Open property detail page
- [ ] Create new property
- [ ] Update existing property
- [ ] Delete property
- [ ] Test offline behavior
- [ ] Test VPN auto-detection (if on VPN)

---

## Error Handling

### Network Errors

```dart
try {
  final properties = await datasource.getProperties();
} on DioException catch (e) {
  if (e.type == DioExceptionType.connectionTimeout) {
    // Show timeout message
  } else if (e.type == DioExceptionType.connectionError) {
    // Show no internet message
  }
}
```

### HTTP Errors

```dart
if (e.response?.statusCode == 401) {
  // Token expired, redirect to login
} else if (e.response?.statusCode == 403) {
  // Insufficient permissions
} else if (e.response?.statusCode == 404) {
  // Resource not found
} else if (e.response?.statusCode >= 500) {
  // Server error
}
```

### User-Friendly Messages

The app converts technical errors to user-friendly messages:

```dart
extension DioExceptionExtension on DioException {
  AppException toAppException() {
    switch (type) {
      case DioExceptionType.connectionTimeout:
        return const NetworkException(message: 'Connection timed out');
      case DioExceptionType.connectionError:
        return const NetworkException(message: 'Unable to connect to server');
      case DioExceptionType.badResponse:
        final statusCode = response?.statusCode;
        final message = response?.data?['message'] ?? 'Server error';
        if (statusCode == 401) {
          return AuthException(message: message, statusCode: statusCode);
        }
        return ServerException(message: message, statusCode: statusCode);
      default:
        return ServerException(message: message ?? 'Unknown error occurred');
    }
  }
}
```

---

## Debugging

### Enable Verbose Logging

The API client includes a logging interceptor that prints all requests/responses:

```dart
// lib/core/network/api_client.dart

class _LoggingInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    debugPrint('API Request: ${options.method} ${options.uri}');
    // Add more logging as needed:
    // debugPrint('Headers: ${options.headers}');
    // debugPrint('Data: ${options.data}');
    return handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    debugPrint('API Response: ${response.statusCode} ${response.requestOptions.uri}');
    // debugPrint('Data: ${response.data}');
    return handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    debugPrint('API Error: ${err.response?.statusCode} ${err.message}');
    // debugPrint('Response: ${err.response?.data}');
    return handler.next(err);
  }
}
```

### Common Debug Logs

```
// Network detection
VPN status: skipped on web (zone detected from URL)
VPN status (cached): false
VPN status (fresh check): true
Using Tailscale URL: https://property.tail58c8e4.ts.net

// Base URL initialization
Base URL initialized to: https://somniproperty.home.lan/api/v1

// API requests
API Request: GET https://somniproperty.home.lan/api/v1/properties?page=1&page_size=50
API Response: 200 https://somniproperty.home.lan/api/v1/properties

// Repository operations
PropertyRepository: Using remote API datasource
PropertyRemoteDataSource: Fetching properties (page: 1, pageSize: 50)
PropertyRemoteDataSource: Received properties response: 200
PropertyRemoteDataSource: Parsed 6 properties
PropertiesNotifier: Loaded 6 properties
```

---

## Switching Between Mock and Real API

To toggle between mock data and the production API:

```dart
// lib/features/properties/presentation/providers/property_provider.dart

/// Provider to control whether to use remote API or mock data
/// Set to true to connect to production backend
const bool _useRemoteApi = true; // Change to false for development with mock data
```

**When to use mock data**:
- Early UI development without backend dependency
- Unit testing
- Offline development
- Demonstrating features without live data

**When to use real API**:
- Integration testing
- End-to-end testing
- Production builds
- Validating backend integration

---

## Next Steps

### Immediate (Priority 1)

1. Add `timezone` field to Property model
2. Integrate Tenants module with remote API
3. Integrate Leases module with remote API
4. Integrate Payments module with remote API
5. Integrate Work Orders module with remote API

### Medium Term (Priority 2)

6. Add WebSocket support for real-time updates
7. Implement request caching (cache GET requests for 1 hour)
8. Add request deduplication (prevent duplicate concurrent requests)
9. Add Sentry error tracking
10. Implement offline-first architecture with local database sync

### Long Term (Priority 3)

11. Integrate remaining backend endpoints (Clients, Quotes, Smart Devices, etc.)
12. Add comprehensive test coverage (unit + integration)
13. Implement optimistic UI updates
14. Add analytics tracking

---

## Support & Troubleshooting

### Common Issues

**Issue**: "Connection refused" error
- **Solution**: Verify backend is running at `https://somniproperty.home.lan`
- **Check**: `curl https://somniproperty.home.lan/api/v1/health`

**Issue**: 401 Unauthorized error
- **Solution**: Token may be expired, logout and login again
- **Check**: Token expiration in secure storage

**Issue**: CORS errors (web builds only)
- **Solution**: Ensure backend CORS configuration allows Flutter web origin
- **Check**: Backend CORS headers include your domain

**Issue**: SSL certificate errors
- **Solution**: For development, you may need to trust self-signed certificates
- **Note**: Production should use valid Let's Encrypt certificates

### Backend Health Check

```bash
# Check if backend is accessible
curl https://somniproperty.home.lan/api/v1/health

# Check properties endpoint (requires auth)
curl -H "Authorization: Bearer <token>" \
  https://somniproperty.home.lan/api/v1/properties
```

---

## Changelog

- **2025-12-05**: Initial integration of Properties module
- **2025-12-05**: Created comprehensive integration guide

---

*Last Updated: December 5, 2025*
