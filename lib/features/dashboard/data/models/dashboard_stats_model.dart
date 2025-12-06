import 'package:somni_property/features/dashboard/domain/entities/dashboard_stats.dart';

/// Dashboard statistics model for JSON serialization
class DashboardStatsModel extends DashboardStats {
  const DashboardStatsModel({
    required super.totalProperties,
    required super.activeTenants,
    required super.monthlyRevenue,
    required super.openWorkOrders,
    required super.availableUnits,
    required super.overduePayments,
    required super.occupancyRate,
    super.propertyTrend,
    super.tenantTrend,
    super.revenueTrend,
  });

  factory DashboardStatsModel.fromJson(Map<String, dynamic> json) {
    return DashboardStatsModel(
      totalProperties: json['total_properties'] as int? ?? 0,
      activeTenants: json['active_tenants'] as int? ?? 0,
      monthlyRevenue: (json['monthly_revenue'] as num?)?.toDouble() ?? 0.0,
      openWorkOrders: json['open_work_orders'] as int? ?? 0,
      availableUnits: json['available_units'] as int? ?? 0,
      overduePayments: (json['overdue_payments'] as num?)?.toDouble() ?? 0.0,
      occupancyRate: (json['occupancy_rate'] as num?)?.toDouble() ?? 0.0,
      propertyTrend: _parseTrend(json['property_trend']),
      tenantTrend: _parseTrend(json['tenant_trend']),
      revenueTrend: _parseTrend(json['revenue_trend']),
    );
  }

  static TrendIndicator _parseTrend(dynamic value) {
    if (value == null) return TrendIndicator.neutral;
    if (value is String) {
      switch (value.toLowerCase()) {
        case 'up':
          return TrendIndicator.up;
        case 'down':
          return TrendIndicator.down;
        default:
          return TrendIndicator.neutral;
      }
    }
    return TrendIndicator.neutral;
  }

  Map<String, dynamic> toJson() {
    return {
      'total_properties': totalProperties,
      'active_tenants': activeTenants,
      'monthly_revenue': monthlyRevenue,
      'open_work_orders': openWorkOrders,
      'available_units': availableUnits,
      'overdue_payments': overduePayments,
      'occupancy_rate': occupancyRate,
      'property_trend': propertyTrend.name,
      'tenant_trend': tenantTrend.name,
      'revenue_trend': revenueTrend.name,
    };
  }
}

/// Revenue data model for JSON serialization
class RevenueDataModel extends RevenueData {
  const RevenueDataModel({
    required super.month,
    required super.amount,
    super.projected,
  });

  factory RevenueDataModel.fromJson(Map<String, dynamic> json) {
    return RevenueDataModel(
      month: DateTime.parse(json['month'] as String),
      amount: (json['amount'] as num).toDouble(),
      projected: (json['projected'] as num?)?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'month': month.toIso8601String(),
      'amount': amount,
      if (projected != null) 'projected': projected,
    };
  }
}

/// Occupancy statistics model
class OccupancyStatsModel extends OccupancyStats {
  const OccupancyStatsModel({
    required super.totalUnits,
    required super.occupiedUnits,
    required super.availableUnits,
    required super.occupancyRate,
  });

  factory OccupancyStatsModel.fromJson(Map<String, dynamic> json) {
    final totalUnits = json['total_units'] as int? ?? 0;
    final occupiedUnits = json['occupied_units'] as int? ?? 0;
    final availableUnits = json['available_units'] as int? ?? (totalUnits - occupiedUnits);
    final occupancyRate = json['occupancy_rate'] as double? ??
        (totalUnits > 0 ? (occupiedUnits / totalUnits * 100) : 0.0);

    return OccupancyStatsModel(
      totalUnits: totalUnits,
      occupiedUnits: occupiedUnits,
      availableUnits: availableUnits,
      occupancyRate: occupancyRate,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_units': totalUnits,
      'occupied_units': occupiedUnits,
      'available_units': availableUnits,
      'occupancy_rate': occupancyRate,
    };
  }
}

/// Work order statistics model
class WorkOrderStatsModel extends WorkOrderStats {
  const WorkOrderStatsModel({
    required super.openCount,
    required super.inProgressCount,
    required super.completedCount,
    required super.criticalCount,
  });

  factory WorkOrderStatsModel.fromJson(Map<String, dynamic> json) {
    return WorkOrderStatsModel(
      openCount: json['open'] as int? ?? 0,
      inProgressCount: json['in_progress'] as int? ?? 0,
      completedCount: json['completed'] as int? ?? 0,
      criticalCount: json['critical'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'open': openCount,
      'in_progress': inProgressCount,
      'completed': completedCount,
      'critical': criticalCount,
    };
  }
}
