import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:somni_property/features/dashboard/domain/entities/dashboard_stats.dart';
import 'package:somni_property/features/dashboard/presentation/widgets/dashboard_stat_card.dart';

void main() {
  group('DashboardStatCard', () {
    testWidgets('should display title and value', (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DashboardStatCard(
              title: 'Total Properties',
              value: '10',
              icon: Icons.apartment,
              color: Colors.blue,
            ),
          ),
        ),
      );

      // Act & Assert
      expect(find.text('Total Properties'), findsOneWidget);
      expect(find.text('10'), findsOneWidget);
      expect(find.byIcon(Icons.apartment), findsOneWidget);
    });

    testWidgets('should display subtitle when provided',
        (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DashboardStatCard(
              title: 'Active Tenants',
              value: '25',
              icon: Icons.people,
              color: Colors.green,
              subtitle: '85% occupied',
            ),
          ),
        ),
      );

      // Act & Assert
      expect(find.text('85% occupied'), findsOneWidget);
    });

    testWidgets('should display trend indicator when provided',
        (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DashboardStatCard(
              title: 'Revenue',
              value: '\$15,000',
              icon: Icons.attach_money,
              color: Colors.amber,
              trend: TrendIndicator.up,
              trendValue: 12.5,
            ),
          ),
        ),
      );

      // Act & Assert
      expect(find.text('12.5%'), findsOneWidget);
      expect(find.byIcon(Icons.trending_up), findsOneWidget);
    });

    testWidgets('should call onTap when tapped', (WidgetTester tester) async {
      // Arrange
      bool wasTapped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DashboardStatCard(
              title: 'Properties',
              value: '10',
              icon: Icons.apartment,
              color: Colors.blue,
              onTap: () {
                wasTapped = true;
              },
            ),
          ),
        ),
      );

      // Act
      await tester.tap(find.byType(DashboardStatCard));
      await tester.pump();

      // Assert
      expect(wasTapped, true);
    });
  });

  group('DashboardStatsGrid', () {
    testWidgets('should display all stat cards', (WidgetTester tester) async {
      // Arrange
      final stats = {
        'totalProperties': 10,
        'activeTenants': 25,
        'monthlyRevenue': 15000.0,
        'openWorkOrders': 5,
        'availableUnits': 3,
        'overduePayments': 500.0,
        'occupancyRate': 89.5,
      };

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DashboardStatsGrid(stats: stats),
          ),
        ),
      );

      // Act & Assert
      expect(find.text('Total Properties'), findsOneWidget);
      expect(find.text('Active Tenants'), findsOneWidget);
      expect(find.text('Monthly Revenue'), findsOneWidget);
      expect(find.text('Open Work Orders'), findsOneWidget);
      expect(find.text('Available Units'), findsOneWidget);
      expect(find.text('Overdue Payments'), findsOneWidget);
    });
  });
}
