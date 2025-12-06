import 'package:equatable/equatable.dart';

/// Overall dashboard statistics entity
class DashboardStats extends Equatable {
  final int totalProperties;
  final int activeTenants;
  final double monthlyRevenue;
  final int openWorkOrders;
  final int availableUnits;
  final double overduePayments;
  final double occupancyRate;
  final TrendIndicator propertyTrend;
  final TrendIndicator tenantTrend;
  final TrendIndicator revenueTrend;

  const DashboardStats({
    required this.totalProperties,
    required this.activeTenants,
    required this.monthlyRevenue,
    required this.openWorkOrders,
    required this.availableUnits,
    required this.overduePayments,
    required this.occupancyRate,
    this.propertyTrend = TrendIndicator.neutral,
    this.tenantTrend = TrendIndicator.neutral,
    this.revenueTrend = TrendIndicator.neutral,
  });

  @override
  List<Object?> get props => [
        totalProperties,
        activeTenants,
        monthlyRevenue,
        openWorkOrders,
        availableUnits,
        overduePayments,
        occupancyRate,
        propertyTrend,
        tenantTrend,
        revenueTrend,
      ];
}

/// Trend indicator for stats
enum TrendIndicator {
  up,
  down,
  neutral;

  /// Get percentage change value for display
  double getPercentage(double current, double previous) {
    if (previous == 0) return 0;
    return ((current - previous) / previous * 100);
  }
}

/// Revenue data for charts
class RevenueData extends Equatable {
  final DateTime month;
  final double amount;
  final double? projected;

  const RevenueData({
    required this.month,
    required this.amount,
    this.projected,
  });

  @override
  List<Object?> get props => [month, amount, projected];
}

/// Occupancy statistics
class OccupancyStats extends Equatable {
  final int totalUnits;
  final int occupiedUnits;
  final int availableUnits;
  final double occupancyRate;

  const OccupancyStats({
    required this.totalUnits,
    required this.occupiedUnits,
    required this.availableUnits,
    required this.occupancyRate,
  });

  @override
  List<Object?> get props => [
        totalUnits,
        occupiedUnits,
        availableUnits,
        occupancyRate,
      ];
}

/// Work order statistics
class WorkOrderStats extends Equatable {
  final int openCount;
  final int inProgressCount;
  final int completedCount;
  final int criticalCount;

  const WorkOrderStats({
    required this.openCount,
    required this.inProgressCount,
    required this.completedCount,
    required this.criticalCount,
  });

  int get total => openCount + inProgressCount + completedCount;

  @override
  List<Object?> get props => [
        openCount,
        inProgressCount,
        completedCount,
        criticalCount,
      ];
}
