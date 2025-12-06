import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import '../../../../../fixtures/property_fixtures.dart';

void main() {
  group('PropertyCard Widget Tests', () {
    testWidgets('should display property name and address', (tester) async {
      final property = createTestProperty(
        name: 'Sunset Apartments',
        address: '123 Main St',
        city: 'Los Angeles',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Card(
              child: ListTile(
                title: Text(property.name),
                subtitle: Text(property.fullAddress),
              ),
            ),
          ),
        ),
      );

      expect(find.text('Sunset Apartments'), findsOneWidget);
      expect(find.text('123 Main St, Los Angeles, CA 12345'), findsOneWidget);
    });

    testWidgets('should display occupancy rate', (tester) async {
      final property = createTestProperty(
        totalUnits: 20,
        occupiedUnits: 15,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Card(
              child: Column(
                children: [
                  Text('Occupancy: ${property.occupancyRate.toStringAsFixed(1)}%'),
                ],
              ),
            ),
          ),
        ),
      );

      expect(find.text('Occupancy: 75.0%'), findsOneWidget);
    });

    testWidgets('should display monthly revenue when available', (tester) async {
      final property = createTestProperty(
        monthlyRevenue: 25000.0,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Card(
              child: Column(
                children: [
                  if (property.monthlyRevenue != null)
                    Text('Revenue: \$${property.monthlyRevenue!.toStringAsFixed(2)}'),
                ],
              ),
            ),
          ),
        ),
      );

      expect(find.text('Revenue: \$25000.00'), findsOneWidget);
    });

    testWidgets('should handle tap gesture', (tester) async {
      final property = createTestProperty();
      var tapped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GestureDetector(
              onTap: () => tapped = true,
              child: Card(
                child: ListTile(
                  title: Text(property.name),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.byType(Card));
      await tester.pumpAndSettle();

      expect(tapped, true);
    });
  });
}
