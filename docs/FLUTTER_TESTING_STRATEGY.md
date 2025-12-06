# Flutter Testing Strategy for SomniProperty

> **Last Updated**: December 5, 2025
> **Target Coverage**: 80%+ across all modules
> **Status**: Implementation in Progress

## Table of Contents

1. [Overview](#overview)
2. [Test Types](#test-types)
3. [Test Structure](#test-structure)
4. [Running Tests](#running-tests)
5. [Coverage Requirements](#coverage-requirements)
6. [Testing Patterns](#testing-patterns)
7. [Test Fixtures](#test-fixtures)
8. [Mock Objects](#mock-objects)
9. [Widget Testing](#widget-testing)
10. [Integration Testing](#integration-testing)
11. [Golden Tests](#golden-tests)
12. [Best Practices](#best-practices)

---

## Overview

SomniProperty uses a comprehensive testing strategy with three layers:
- **Unit Tests**: Test business logic, models, and repositories
- **Widget Tests**: Test UI components and screens
- **Integration Tests**: Test complete user flows

### Testing Dependencies

```yaml
dev_dependencies:
  flutter_test:
    sdk: flutter
  integration_test:
    sdk: flutter
  mockito: ^5.4.4
  mocktail: ^1.0.1
  fake_async: ^1.3.1
  bloc_test: ^9.1.5
  coverage: ^1.7.1
```

---

## Test Types

### 1. Unit Tests

Test individual units of code in isolation:
- **Entities**: Domain models with business logic
- **Models**: Data models with JSON serialization
- **Repositories**: Data access layer
- **Use Cases**: Business logic operations
- **Providers**: State management

**Location**: `test/features/{module}/{layer}/{component}_test.dart`

**Example**:
```dart
test/features/properties/domain/entities/property_test.dart
test/features/properties/data/models/property_model_test.dart
test/features/properties/data/repositories/property_repository_test.dart
```

### 2. Widget Tests

Test UI components and their interactions:
- **Screens**: Full screen widgets
- **Cards**: Individual card components
- **Forms**: Input forms with validation
- **Dialogs**: Modal dialogs and bottom sheets

**Location**: `test/features/{module}/presentation/widgets/{widget}_test.dart`

**Example**:
```dart
test/features/properties/presentation/widgets/property_card_test.dart
test/features/properties/presentation/pages/properties_list_test.dart
```

### 3. Integration Tests

Test complete user flows end-to-end:
- **CRUD Operations**: Create, read, update, delete flows
- **Navigation**: Multi-screen workflows
- **API Integration**: Backend communication (mocked)

**Location**: `integration_test/{flow}_test.dart`

**Example**:
```dart
integration_test/property_management_flow_test.dart
integration_test/tenant_onboarding_flow_test.dart
```

---

## Test Structure

### Standard Test File Structure

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:somni_property/features/{module}/{layer}/{component}.dart';
import '../../../fixtures/{module}_fixtures.dart';

void main() {
  group('{Component} Tests', () {
    late {Type} testObject;

    setUp(() {
      // Setup before each test
      testObject = createTest{Component}();
    });

    tearDown(() {
      // Cleanup after each test
    });

    group('{Feature Group}', () {
      test('should {expected behavior}', () {
        // Arrange
        final input = testObject.copyWith(field: newValue);

        // Act
        final result = input.someMethod();

        // Assert
        expect(result, expectedValue);
      });
    });
  });
}
```

### Naming Conventions

- **Test files**: End with `_test.dart`
- **Test groups**: Use `group()` for logical grouping
- **Test names**: Use descriptive names starting with "should"

**Examples**:
- ✅ `test('should calculate occupancy rate correctly', () {...})`
- ✅ `test('should return error when property not found', () {...})`
- ❌ `test('test1', () {...})`

---

## Running Tests

### Run All Tests

```bash
flutter test
```

### Run Specific Test File

```bash
flutter test test/features/properties/domain/entities/property_test.dart
```

### Run Tests by Pattern

```bash
# Run all property tests
flutter test test/features/properties

# Run all model tests
flutter test --name "Model"
```

### Run Tests with Coverage

```bash
# Generate coverage data
flutter test --coverage

# Generate HTML report
genhtml coverage/lcov.info -o coverage/html

# Open report in browser
open coverage/html/index.html  # macOS
xdg-open coverage/html/index.html  # Linux
start coverage/html/index.html  # Windows
```

### Watch Mode (Auto-run on changes)

```bash
flutter test --watch
```

---

## Coverage Requirements

### Module-Level Targets

| Module | Target Coverage | Status |
|--------|----------------|--------|
| Properties | 80%+ | ✅ Complete |
| Tenants | 80%+ | ✅ Complete |
| Leases | 80%+ | ✅ Complete |
| Payments | 80%+ | ✅ Complete |
| Work Orders | 80%+ | 🚧 In Progress |
| Dashboard | 75%+ | 📋 Pending |
| Contractors | 80%+ | 📋 Pending |
| Quotes | 80%+ | 📋 Pending |

### Layer-Level Targets

- **Domain Layer**: 90%+ (critical business logic)
- **Data Layer**: 85%+ (models, repositories)
- **Presentation Layer**: 70%+ (UI components)

---

## Testing Patterns

### Pattern 1: Entity Testing

Test domain entities with computed properties:

```dart
group('Property Entity', () {
  test('should calculate occupancy rate correctly', () {
    final property = createTestProperty(
      totalUnits: 20,
      occupiedUnits: 15,
    );

    expect(property.occupancyRate, 75.0);
  });

  test('should identify fully occupied properties', () {
    final property = createTestProperty(
      totalUnits: 10,
      occupiedUnits: 10,
    );

    expect(property.isFullyOccupied, true);
  });
});
```

### Pattern 2: Model JSON Testing

Test serialization and deserialization:

```dart
group('PropertyModel', () {
  group('fromJson', () {
    test('should deserialize valid JSON', () {
      final json = propertyJsonFixture();
      final model = PropertyModel.fromJson(json);

      expect(model.id, json['id']);
      expect(model.name, json['name']);
      expect(model.type, PropertyType.apartment);
    });

    test('should handle missing optional fields', () {
      final minimalJson = {'id': '1', 'name': 'Test', ...};
      final model = PropertyModel.fromJson(minimalJson);

      expect(model.description, null);
      expect(model.monthlyRevenue, null);
    });
  });

  group('toJson', () {
    test('should serialize to valid JSON', () {
      final model = createTestPropertyModel();
      final json = model.toJson();

      expect(json['id'], model.id);
      expect(json['name'], model.name);
      expect(json['type'], model.type.name);
    });
  });

  test('should maintain data through JSON round-trip', () {
    final original = createTestPropertyModel();
    final json = original.toJson();
    final reconstructed = PropertyModel.fromJson(json);

    expect(reconstructed, equals(original));
  });
});
```

### Pattern 3: Repository Testing with Mocks

Test repositories with mocked data sources:

```dart
import 'package:mocktail/mocktail.dart';

class MockPropertyRemoteDataSource extends Mock
    implements PropertyRemoteDataSource {}

void main() {
  late PropertyRepositoryImpl repository;
  late MockPropertyRemoteDataSource mockRemoteDataSource;

  setUp(() {
    mockRemoteDataSource = MockPropertyRemoteDataSource();
    repository = PropertyRepositoryImpl(mockRemoteDataSource);
  });

  test('should return properties when remote call succeeds', () async {
    // Arrange
    final properties = [createTestPropertyModel()];
    when(() => mockRemoteDataSource.getProperties())
        .thenAnswer((_) async => properties);

    // Act
    final result = await repository.getProperties();

    // Assert
    expect(result.isRight(), true);
    result.fold(
      (failure) => fail('Should not return failure'),
      (data) => expect(data, properties),
    );
    verify(() => mockRemoteDataSource.getProperties()).called(1);
  });

  test('should return failure when remote call throws exception', () async {
    // Arrange
    when(() => mockRemoteDataSource.getProperties())
        .thenThrow(ServerException('Connection failed'));

    // Act
    final result = await repository.getProperties();

    // Assert
    expect(result.isLeft(), true);
    result.fold(
      (failure) => expect(failure, isA<ServerFailure>()),
      (data) => fail('Should not return success'),
    );
  });
}
```

### Pattern 4: Provider/State Testing

Test Riverpod providers:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() {
  test('should load properties successfully', () async {
    final container = ProviderContainer(
      overrides: [
        propertyRepositoryProvider.overrideWithValue(mockRepository),
      ],
    );

    when(() => mockRepository.getProperties())
        .thenAnswer((_) async => Right([createTestProperty()]));

    final provider = container.read(propertiesProvider.notifier);
    await provider.loadProperties();

    final state = container.read(propertiesProvider);
    expect(state.isLoading, false);
    expect(state.properties.length, 1);
  });
}
```

---

## Test Fixtures

Fixtures provide reusable test data.

### Location

`test/fixtures/{module}_fixtures.dart`

### Creating Fixtures

```dart
// test/fixtures/property_fixtures.dart

/// Create a test Property entity
Property createTestProperty({
  String id = 'test-property-1',
  String name = 'Test Property',
  int totalUnits = 10,
  int occupiedUnits = 7,
  // ... other parameters with defaults
}) {
  return Property(
    id: id,
    name: name,
    totalUnits: totalUnits,
    occupiedUnits: occupiedUnits,
    // ... other fields
  );
}

/// Create a list of test properties
List<Property> createTestPropertiesList({int count = 3}) {
  return List.generate(
    count,
    (index) => createTestProperty(id: 'property-$index'),
  );
}

/// Sample JSON response
Map<String, dynamic> propertyJsonFixture({String id = 'test-1'}) {
  return {
    'id': id,
    'name': 'Test Property',
    'address': '123 Main St',
    // ... other fields
  };
}
```

### Using Fixtures

```dart
test('should process property correctly', () {
  final property = createTestProperty(occupiedUnits: 8);
  // Test with fixture data
});
```

---

## Mock Objects

### Creating Mocks with Mocktail

```dart
import 'package:mocktail/mocktail.dart';

class MockPropertyRepository extends Mock implements PropertyRepository {}
class MockDio extends Mock implements Dio {}
```

### Setting Up Mocks

```dart
setUp(() {
  mockRepository = MockPropertyRepository();

  // Setup default behaviors
  when(() => mockRepository.getProperties())
      .thenAnswer((_) async => Right([]));
});
```

### Stubbing Methods

```dart
// Return a value
when(() => mock.someMethod()).thenReturn(value);

// Return a Future
when(() => mock.asyncMethod()).thenAnswer((_) async => value);

// Throw an exception
when(() => mock.failingMethod()).thenThrow(Exception('Error'));

// Match any argument
when(() => mock.methodWithArg(any())).thenReturn(value);

// Match specific argument
when(() => mock.methodWithArg('specific')).thenReturn(value);
```

### Verifying Calls

```dart
// Verify method was called once
verify(() => mock.someMethod()).called(1);

// Verify method was never called
verifyNever(() => mock.someMethod());

// Verify method was called with specific args
verify(() => mock.methodWithArg('value')).called(1);
```

---

## Widget Testing

### Basic Widget Test

```dart
testWidgets('should display property name', (tester) async {
  final property = createTestProperty(name: 'Sunset Apartments');

  await tester.pumpWidget(
    MaterialApp(
      home: PropertyCard(property: property),
    ),
  );

  expect(find.text('Sunset Apartments'), findsOneWidget);
});
```

### Testing User Interactions

```dart
testWidgets('should navigate on tap', (tester) async {
  await tester.pumpWidget(
    MaterialApp(
      home: PropertyList(),
      routes: {
        '/details': (context) => PropertyDetails(),
      },
    ),
  );

  // Tap on first property card
  await tester.tap(find.byType(PropertyCard).first);
  await tester.pumpAndSettle();

  // Verify navigation
  expect(find.byType(PropertyDetails), findsOneWidget);
});
```

### Testing Forms

```dart
testWidgets('should validate email field', (tester) async {
  await tester.pumpWidget(
    MaterialApp(home: TenantForm()),
  );

  // Enter invalid email
  await tester.enterText(find.byKey(Key('email')), 'invalid');
  await tester.tap(find.text('Submit'));
  await tester.pump();

  // Verify error message
  expect(find.text('Invalid email'), findsOneWidget);
});
```

### Testing with Riverpod

```dart
testWidgets('should display loading state', (tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        propertiesProvider.overrideWith((ref) {
          return PropertiesState(isLoading: true, properties: []);
        }),
      ],
      child: MaterialApp(home: PropertyList()),
    ),
  );

  expect(find.byType(CircularProgressIndicator), findsOneWidget);
});
```

---

## Integration Testing

### Setup

```dart
// integration_test/property_flow_test.dart

import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:somni_property/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Property Management Flow', () {
    testWidgets('complete CRUD flow', (tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Login
      await tester.enterText(find.byKey(Key('email')), 'test@example.com');
      await tester.enterText(find.byKey(Key('password')), 'password');
      await tester.tap(find.text('Login'));
      await tester.pumpAndSettle();

      // Navigate to properties
      await tester.tap(find.text('Properties'));
      await tester.pumpAndSettle();

      // Add new property
      await tester.tap(find.byIcon(Icons.add));
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(Key('name')), 'New Property');
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      // Verify property appears in list
      expect(find.text('New Property'), findsOneWidget);
    });
  });
}
```

### Running Integration Tests

```bash
flutter test integration_test/
```

---

## Golden Tests

Golden tests capture widget screenshots for visual regression testing.

### Creating Golden Tests

```dart
testWidgets('property card golden test', (tester) async {
  await tester.pumpWidget(
    MaterialApp(
      home: PropertyCard(property: createTestProperty()),
    ),
  );

  await expectLater(
    find.byType(PropertyCard),
    matchesGoldenFile('goldens/property_card.png'),
  );
});
```

### Generating Goldens

```bash
flutter test --update-goldens
```

### Best Practices

- Generate goldens on a consistent platform (CI/CD)
- Test multiple states (empty, loading, error, success)
- Test different screen sizes
- Store goldens in `test/goldens/` directory

---

## Best Practices

### 1. Test Organization

- ✅ One test file per source file
- ✅ Group related tests with `group()`
- ✅ Use descriptive test names
- ✅ Follow Arrange-Act-Assert pattern

### 2. Test Independence

- ✅ Each test should be independent
- ✅ Use `setUp()` and `tearDown()`
- ✅ Don't rely on test execution order
- ❌ Don't share mutable state between tests

### 3. Mocking

- ✅ Mock external dependencies (APIs, databases)
- ✅ Use fixtures for test data
- ✅ Verify mock interactions
- ❌ Don't mock what you don't own (Flutter framework)

### 4. Coverage

- ✅ Aim for 80%+ coverage
- ✅ Focus on critical business logic
- ✅ Test edge cases and error paths
- ❌ Don't chase 100% coverage

### 5. Performance

- ✅ Keep tests fast (< 1 second each)
- ✅ Use `pumpAndSettle()` sparingly
- ✅ Mock slow operations
- ❌ Don't include unnecessary delays

### 6. Maintenance

- ✅ Keep fixtures up-to-date
- ✅ Refactor tests when refactoring code
- ✅ Remove obsolete tests
- ✅ Document complex test scenarios

---

## Test Coverage Scripts

### Generate Coverage Report

```bash
#!/bin/bash
# scripts/test_coverage.sh

flutter test --coverage
genhtml coverage/lcov.info -o coverage/html
echo "Coverage report generated at coverage/html/index.html"
```

### Check Coverage Threshold

```bash
#!/bin/bash
# scripts/check_coverage.sh

flutter test --coverage
COVERAGE=$(lcov --summary coverage/lcov.info 2>&1 | grep "lines" | awk '{print $2}' | cut -d'%' -f1)

if (( $(echo "$COVERAGE < 80" | bc -l) )); then
  echo "Coverage $COVERAGE% is below 80% threshold"
  exit 1
else
  echo "Coverage $COVERAGE% meets threshold"
  exit 0
fi
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: subosito/flutter-action@v2
      - run: flutter pub get
      - run: flutter test --coverage
      - run: genhtml coverage/lcov.info -o coverage/html
      - uses: codecov/codecov-action@v3
        with:
          files: coverage/lcov.info
```

---

## Common Issues

### Issue: "flutter: command not found"

Tests require Flutter SDK. Install Flutter or run tests in CI with Flutter action.

### Issue: "Missing coverage data"

Run tests with `--coverage` flag:
```bash
flutter test --coverage
```

### Issue: "Golden file mismatch"

Regenerate goldens on same platform:
```bash
flutter test --update-goldens
```

### Issue: "Provider not found"

Wrap widget tests with `ProviderScope`:
```dart
await tester.pumpWidget(
  ProviderScope(child: MyApp()),
);
```

---

## Resources

- [Flutter Testing Documentation](https://docs.flutter.dev/testing)
- [Mockito Documentation](https://pub.dev/packages/mockito)
- [Mocktail Documentation](https://pub.dev/packages/mocktail)
- [Riverpod Testing](https://riverpod.dev/docs/essentials/testing)
- [Integration Testing](https://docs.flutter.dev/testing/integration-tests)

---

## Appendix: Complete Test Examples

### Complete Entity Test

See: `test/features/properties/domain/entities/property_test.dart`

### Complete Model Test

See: `test/features/properties/data/models/property_model_test.dart`

### Complete Widget Test

See: `test/features/properties/presentation/widgets/property_card_test.dart`

### Complete Integration Test

See: `integration_test/property_management_flow_test.dart`

---

**Last Updated**: December 5, 2025
**Maintained By**: SomniProperty Development Team
