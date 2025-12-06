import 'package:mocktail/mocktail.dart';
import 'package:dio/dio.dart';
import 'package:somni_property/features/properties/domain/repositories/property_repository.dart';
import 'package:somni_property/features/tenants/domain/repositories/tenant_repository.dart';
import 'package:somni_property/features/leases/domain/repositories/lease_repository.dart';
import 'package:somni_property/features/payments/domain/repositories/payment_repository.dart';

/// Mock PropertyRepository
class MockPropertyRepository extends Mock implements PropertyRepository {}

/// Mock TenantRepository
class MockTenantRepository extends Mock implements TenantRepository {}

/// Mock LeaseRepository
class MockLeaseRepository extends Mock implements LeaseRepository {}

/// Mock PaymentRepository
class MockPaymentRepository extends Mock implements PaymentRepository {}

/// Mock Dio HTTP client
class MockDio extends Mock implements Dio {}

/// Mock Response
class MockResponse<T> extends Mock implements Response<T> {}

/// Setup Mocktail fallback values
void setupMocktailFallbacks() {
  // Register fallback values for common types
  registerFallbackValue(RequestOptions(path: ''));
  registerFallbackValue(Uri.parse('https://test.com'));
}
