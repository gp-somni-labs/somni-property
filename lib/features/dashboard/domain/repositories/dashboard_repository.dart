import 'package:dartz/dartz.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/dashboard/domain/entities/activity_item.dart';
import 'package:somni_property/features/dashboard/domain/entities/alert.dart';
import 'package:somni_property/features/dashboard/domain/entities/dashboard_stats.dart';

/// Repository interface for dashboard data
abstract class DashboardRepository {
  /// Get overall dashboard statistics
  Future<Either<Failure, DashboardStats>> getStats();

  /// Get revenue data for charts
  Future<Either<Failure, List<RevenueData>>> getRevenue({int months = 12});

  /// Get occupancy statistics
  Future<Either<Failure, OccupancyStats>> getOccupancy();

  /// Get work order metrics
  Future<Either<Failure, WorkOrderStats>> getWorkOrders();

  /// Get recent activity feed
  Future<Either<Failure, List<ActivityItem>>> getActivity({int limit = 20});

  /// Get urgent alerts
  Future<Either<Failure, List<Alert>>> getAlerts();

  /// Get upcoming events
  Future<Either<Failure, List<UpcomingEvent>>> getUpcoming({int days = 30});

  /// Dismiss an alert
  Future<Either<Failure, void>> dismissAlert(String alertId);

  /// Get all dashboard data in one call (for initial load)
  Future<Either<Failure, DashboardData>> getAllData();
}

/// Aggregated dashboard data for initial load
class DashboardData {
  final DashboardStats stats;
  final List<RevenueData> revenue;
  final OccupancyStats occupancy;
  final WorkOrderStats workOrders;
  final List<ActivityItem> activity;
  final List<Alert> alerts;
  final List<UpcomingEvent> upcomingEvents;

  const DashboardData({
    required this.stats,
    required this.revenue,
    required this.occupancy,
    required this.workOrders,
    required this.activity,
    required this.alerts,
    required this.upcomingEvents,
  });
}
