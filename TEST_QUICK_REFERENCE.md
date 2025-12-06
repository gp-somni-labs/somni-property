# Flutter Testing Quick Reference - SomniProperty

Quick reference for running tests and understanding the test structure.

## Quick Commands

```bash
# Run all tests
flutter test

# Run with coverage
flutter test --coverage

# Run specific module
flutter test test/features/properties

# Run specific test file
flutter test test/features/properties/domain/entities/property_test.dart

# Watch mode (auto-rerun on changes)
flutter test --watch

# Generate coverage report
./scripts/test_coverage.sh

# Update golden files
flutter test --update-goldens
```

## Test File Structure

```
test/
├── fixtures/                          # Test data generators
│   ├── property_fixtures.dart
│   ├── tenant_fixtures.dart
│   └── lease_fixtures.dart
├── helpers/                           # Test utilities
│   ├── test_helpers.dart
│   └── mock_providers.dart
└── features/
    ├── properties/
    │   ├── domain/entities/           # Entity tests
    │   ├── data/models/               # Model tests
    │   └── presentation/widgets/      # Widget tests
    ├── tenants/
    ├── leases/
    └── payments/
```

## Creating a New Test

### 1. Create Fixture (if needed)

```dart
// test/fixtures/module_fixtures.dart

ModuleEntity createTestModule({
  String id = 'test-1',
  String name = 'Test Module',
  // ... other parameters with defaults
}) {
  return ModuleEntity(
    id: id,
    name: name,
    // ... other fields
  );
}
```

### 2. Create Entity Test

```dart
// test/features/module/domain/entities/module_test.dart

import 'package:flutter_test/flutter_test.dart';
import '../../../fixtures/module_fixtures.dart';

void main() {
  group('Module Entity', () {
    test('should compute property correctly', () {
      final entity = createTestModule(field: value);
      expect(entity.computedProperty, expectedValue);
    });
  });
}
```

### 3. Create Model Test

```dart
// test/features/module/data/models/module_model_test.dart

group('ModuleModel', () {
  group('fromJson', () {
    test('should deserialize valid JSON', () {
      final json = moduleJsonFixture();
      final model = ModuleModel.fromJson(json);
      expect(model.id, json['id']);
    });
  });

  group('toJson', () {
    test('should serialize to valid JSON', () {
      final model = createTestModuleModel();
      final json = model.toJson();
      expect(json['id'], model.id);
    });
  });
});
```

## Common Test Patterns

### Testing Computed Properties

```dart
test('should calculate value correctly', () {
  final entity = createTestEntity(a: 10, b: 20);
  expect(entity.sum, 30);
});
```

### Testing Equality

```dart
test('should be equal with same values', () {
  final entity1 = createTestEntity(id: '1');
  final entity2 = createTestEntity(id: '1');
  expect(entity1, equals(entity2));
});
```

### Testing JSON Deserialization

```dart
test('should deserialize valid JSON', () {
  final json = {'id': '1', 'name': 'Test'};
  final model = Model.fromJson(json);
  expect(model.id, '1');
  expect(model.name, 'Test');
});
```

### Testing JSON Serialization

```dart
test('should serialize to JSON', () {
  final model = createTestModel();
  final json = model.toJson();
  expect(json['id'], model.id);
});
```

### Testing with Mocks

```dart
test('should return data when successful', () async {
  when(() => mockRepository.getData())
      .thenAnswer((_) async => Right(testData));

  final result = await repository.getData();

  expect(result.isRight(), true);
  verify(() => mockRepository.getData()).called(1);
});
```

### Testing Widgets

```dart
testWidgets('should display text', (tester) async {
  await tester.pumpWidget(
    MaterialApp(home: MyWidget(text: 'Hello')),
  );

  expect(find.text('Hello'), findsOneWidget);
});
```

## Coverage Targets

- **Domain (Entities)**: 90%+
- **Data (Models, Repositories)**: 85%+
- **Presentation (Widgets)**: 70%+
- **Overall App**: 80%+

## Test File Checklist

When creating tests for a new module:

- [ ] Create fixtures in `test/fixtures/{module}_fixtures.dart`
- [ ] Test entity in `test/features/{module}/domain/entities/`
- [ ] Test model JSON in `test/features/{module}/data/models/`
- [ ] Test model serialization
- [ ] Test enums (if any)
- [ ] Test computed properties
- [ ] Test equality and copyWith
- [ ] Run coverage: `flutter test --coverage`
- [ ] Verify 80%+ coverage

## Documentation

- **Full Guide**: `docs/FLUTTER_TESTING_STRATEGY.md`
- **Implementation Report**: `FLUTTER_TESTING_IMPLEMENTATION_REPORT.md`
- **This Reference**: `TEST_QUICK_REFERENCE.md`

## Common Issues

### Flutter not found
```bash
# Add Flutter to PATH or use full path
export PATH="$PATH:/path/to/flutter/bin"
```

### Tests not running
```bash
# Clean and get dependencies
flutter clean
flutter pub get
flutter test
```

### Coverage not generating
```bash
# Install lcov (Ubuntu/Debian)
sudo apt-get install lcov

# Install lcov (macOS)
brew install lcov
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
- name: Run Tests
  run: flutter test --coverage

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: coverage/lcov.info
```

## Need Help?

1. Check `docs/FLUTTER_TESTING_STRATEGY.md` for detailed examples
2. Look at existing tests for patterns
3. Review fixtures for test data generators
4. Run `flutter test --help` for command options

---

**Last Updated**: December 5, 2025
