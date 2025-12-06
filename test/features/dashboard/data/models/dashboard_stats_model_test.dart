import 'package:flutter_test/flutter_test.dart';
import 'package:somni_property/features/dashboard/data/models/dashboard_stats_model.dart';
import 'package:somni_property/features/dashboard/domain/entities/dashboard_stats.dart';

void main() {
  group('DashboardStatsModel', () {
    test('should parse from JSON correctly', () {
      // Arrange
      final json = {
        'total_properties': 10,
        'active_tenants': 25,
        'monthly_revenue': 15000.0,
        'open_work_orders': 5,
        'available_units': 3,
        'overdue_payments': 500.0,
        'occupancy_rate': 89.5,
        'property_trend': 'up',
        'tenant_trend': 'neutral',
        'revenue_trend': 'up',
      };

      // Act
      final model = DashboardStatsModel.fromJson(json);

      // Assert
      expect(model.totalProperties, 10);
      expect(model.activeTenants, 25);
      expect(model.monthlyRevenue, 15000.0);
      expect(model.openWorkOrders, 5);
      expect(model.availableUnits, 3);
      expect(model.overduePayments, 500.0);
      expect(model.occupancyRate, 89.5);
      expect(model.propertyTrend, TrendIndicator.up);
      expect(model.tenantTrend, TrendIndicator.neutral);
      expect(model.revenueTrend, TrendIndicator.up);
    });

    test('should handle missing optional fields', () {
      // Arrange
      final json = {
        'total_properties': 5,
        'active_tenants': 10,
        'monthly_revenue': 5000.0,
        'open_work_orders': 0,
        'available_units': 2,
        'overdue_payments': 0.0,
        'occupancy_rate': 80.0,
      };

      // Act
      final model = DashboardStatsModel.fromJson(json);

      // Assert
      expect(model.totalProperties, 5);
      expect(model.propertyTrend, TrendIndicator.neutral);
      expect(model.tenantTrend, TrendIndicator.neutral);
      expect(model.revenueTrend, TrendIndicator.neutral);
    });

    test('should convert to JSON correctly', () {
      // Arrange
      const model = DashboardStatsModel(
        totalProperties: 10,
        activeTenants: 25,
        monthlyRevenue: 15000.0,
        openWorkOrders: 5,
        availableUnits: 3,
        overduePayments: 500.0,
        occupancyRate: 89.5,
        propertyTrend: TrendIndicator.up,
        tenantTrend: TrendIndicator.neutral,
        revenueTrend: TrendIndicator.up,
      );

      // Act
      final json = model.toJson();

      // Assert
      expect(json['total_properties'], 10);
      expect(json['active_tenants'], 25);
      expect(json['monthly_revenue'], 15000.0);
      expect(json['property_trend'], 'up');
      expect(json['tenant_trend'], 'neutral');
      expect(json['revenue_trend'], 'up');
    });
  });

  group('RevenueDataModel', () {
    test('should parse from JSON correctly', () {
      // Arrange
      final json = {
        'month': '2024-01-01T00:00:00.000Z',
        'amount': 5000.0,
        'projected': 5500.0,
      };

      // Act
      final model = RevenueDataModel.fromJson(json);

      // Assert
      expect(model.month, DateTime.parse('2024-01-01T00:00:00.000Z'));
      expect(model.amount, 5000.0);
      expect(model.projected, 5500.0);
    });

    test('should handle missing projected field', () {
      // Arrange
      final json = {
        'month': '2024-01-01T00:00:00.000Z',
        'amount': 5000.0,
      };

      // Act
      final model = RevenueDataModel.fromJson(json);

      // Assert
      expect(model.month, DateTime.parse('2024-01-01T00:00:00.000Z'));
      expect(model.amount, 5000.0);
      expect(model.projected, null);
    });
  });

  group('OccupancyStatsModel', () {
    test('should parse from JSON correctly', () {
      // Arrange
      final json = {
        'total_units': 100,
        'occupied_units': 85,
        'available_units': 15,
        'occupancy_rate': 85.0,
      };

      // Act
      final model = OccupancyStatsModel.fromJson(json);

      // Assert
      expect(model.totalUnits, 100);
      expect(model.occupiedUnits, 85);
      expect(model.availableUnits, 15);
      expect(model.occupancyRate, 85.0);
    });

    test('should calculate occupancy rate when not provided', () {
      // Arrange
      final json = {
        'total_units': 100,
        'occupied_units': 75,
      };

      // Act
      final model = OccupancyStatsModel.fromJson(json);

      // Assert
      expect(model.occupancyRate, 75.0);
      expect(model.availableUnits, 25);
    });
  });

  group('WorkOrderStatsModel', () {
    test('should parse from JSON correctly', () {
      // Arrange
      final json = {
        'open': 5,
        'in_progress': 3,
        'completed': 10,
        'critical': 2,
      };

      // Act
      final model = WorkOrderStatsModel.fromJson(json);

      // Assert
      expect(model.openCount, 5);
      expect(model.inProgressCount, 3);
      expect(model.completedCount, 10);
      expect(model.criticalCount, 2);
      expect(model.total, 18);
    });
  });
}
