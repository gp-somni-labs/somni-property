import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/dashboard/data/datasources/dashboard_remote_datasource.dart';
import 'package:somni_property/features/dashboard/data/repositories/dashboard_repository_impl.dart';
import 'package:somni_property/features/dashboard/domain/entities/activity_item.dart';
import 'package:somni_property/features/dashboard/domain/entities/alert.dart';
import 'package:somni_property/features/dashboard/domain/entities/dashboard_stats.dart';
import 'package:somni_property/features/dashboard/domain/repositories/dashboard_repository.dart';

/// Provider for DashboardRemoteDataSource
final dashboardRemoteDataSourceProvider =
    Provider<DashboardRemoteDataSource>((ref) {
  return DashboardRemoteDataSourceImpl(
    apiClient: ref.watch(apiClientProvider),
  );
});

/// Provider for DashboardRepository
final dashboardRepositoryProvider = Provider<DashboardRepository>((ref) {
  return DashboardRepositoryImpl(
    remoteDataSource: ref.watch(dashboardRemoteDataSourceProvider),
  );
});

/// State for dashboard data
class DashboardState {
  final DashboardStats? stats;
  final List<RevenueData> revenue;
  final OccupancyStats? occupancy;
  final WorkOrderStats? workOrders;
  final List<ActivityItem> activity;
  final List<Alert> alerts;
  final List<UpcomingEvent> upcomingEvents;
  final bool isLoading;
  final String? error;
  final DateTime? lastRefresh;

  const DashboardState({
    this.stats,
    this.revenue = const [],
    this.occupancy,
    this.workOrders,
    this.activity = const [],
    this.alerts = const [],
    this.upcomingEvents = const [],
    this.isLoading = false,
    this.error,
    this.lastRefresh,
  });

  DashboardState copyWith({
    DashboardStats? stats,
    List<RevenueData>? revenue,
    OccupancyStats? occupancy,
    WorkOrderStats? workOrders,
    List<ActivityItem>? activity,
    List<Alert>? alerts,
    List<UpcomingEvent>? upcomingEvents,
    bool? isLoading,
    String? error,
    DateTime? lastRefresh,
    bool clearError = false,
  }) {
    return DashboardState(
      stats: stats ?? this.stats,
      revenue: revenue ?? this.revenue,
      occupancy: occupancy ?? this.occupancy,
      workOrders: workOrders ?? this.workOrders,
      activity: activity ?? this.activity,
      alerts: alerts ?? this.alerts,
      upcomingEvents: upcomingEvents ?? this.upcomingEvents,
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      lastRefresh: lastRefresh ?? this.lastRefresh,
    );
  }

  /// Check if data is empty
  bool get isEmpty => stats == null && activity.isEmpty && alerts.isEmpty;

  /// Check if data needs refresh (older than 5 minutes)
  bool get needsRefresh {
    if (lastRefresh == null) return true;
    final now = DateTime.now();
    final difference = now.difference(lastRefresh!);
    return difference.inMinutes >= 5;
  }

  /// Group activities by date
  Map<String, List<ActivityItem>> get groupedActivities {
    final groups = <String, List<ActivityItem>>{};

    for (final item in activity) {
      final group = item.dateGroup;
      if (!groups.containsKey(group)) {
        groups[group] = [];
      }
      groups[group]!.add(item);
    }

    return groups;
  }

  /// Get alerts by priority
  List<Alert> getAlertsByPriority(AlertPriority priority) {
    return alerts.where((alert) => alert.priority == priority).toList();
  }

  /// Get critical alerts count
  int get criticalAlertsCount =>
      alerts.where((a) => a.priority == AlertPriority.critical).length;

  /// Get high priority alerts count
  int get highPriorityAlertsCount =>
      alerts.where((a) => a.priority == AlertPriority.high).length;
}

/// Dashboard state notifier
class DashboardNotifier extends StateNotifier<DashboardState> {
  final DashboardRepository repository;
  Timer? _autoRefreshTimer;

  DashboardNotifier({required this.repository})
      : super(const DashboardState()) {
    loadAllData();
    _startAutoRefresh();
  }

  /// Load all dashboard data
  Future<void> loadAllData() async {
    state = state.copyWith(isLoading: true, clearError: true);

    final result = await repository.getAllData();

    result.fold(
      (failure) {
        debugPrint('DashboardNotifier: Load failed: ${failure.message}');
        state = state.copyWith(
          isLoading: false,
          error: failure.message,
        );
      },
      (data) {
        debugPrint('DashboardNotifier: Loaded all dashboard data');
        state = state.copyWith(
          isLoading: false,
          stats: data.stats,
          revenue: data.revenue,
          occupancy: data.occupancy,
          workOrders: data.workOrders,
          activity: data.activity,
          alerts: data.alerts,
          upcomingEvents: data.upcomingEvents,
          lastRefresh: DateTime.now(),
        );
      },
    );
  }

  /// Refresh dashboard data
  Future<void> refresh() async {
    await loadAllData();
  }

  /// Load only stats (lighter operation)
  Future<void> loadStats() async {
    final result = await repository.getStats();

    result.fold(
      (failure) {
        debugPrint('DashboardNotifier: Stats load failed: ${failure.message}');
      },
      (stats) {
        debugPrint('DashboardNotifier: Loaded stats');
        state = state.copyWith(
          stats: stats,
          lastRefresh: DateTime.now(),
        );
      },
    );
  }

  /// Load only activity feed
  Future<void> loadActivity() async {
    final result = await repository.getActivity(limit: 20);

    result.fold(
      (failure) {
        debugPrint(
            'DashboardNotifier: Activity load failed: ${failure.message}');
      },
      (activity) {
        debugPrint('DashboardNotifier: Loaded ${activity.length} activities');
        state = state.copyWith(activity: activity);
      },
    );
  }

  /// Load only alerts
  Future<void> loadAlerts() async {
    final result = await repository.getAlerts();

    result.fold(
      (failure) {
        debugPrint('DashboardNotifier: Alerts load failed: ${failure.message}');
      },
      (alerts) {
        debugPrint('DashboardNotifier: Loaded ${alerts.length} alerts');
        state = state.copyWith(alerts: alerts);
      },
    );
  }

  /// Dismiss an alert
  Future<bool> dismissAlert(String alertId) async {
    final result = await repository.dismissAlert(alertId);

    return result.fold(
      (failure) {
        debugPrint('DashboardNotifier: Dismiss failed: ${failure.message}');
        return false;
      },
      (_) {
        debugPrint('DashboardNotifier: Alert dismissed');
        // Remove alert from state
        final updatedAlerts =
            state.alerts.where((alert) => alert.id != alertId).toList();
        state = state.copyWith(alerts: updatedAlerts);
        return true;
      },
    );
  }

  /// Start auto-refresh timer (every 5 minutes)
  void _startAutoRefresh() {
    _autoRefreshTimer?.cancel();
    _autoRefreshTimer = Timer.periodic(
      const Duration(minutes: 5),
      (_) {
        if (state.needsRefresh) {
          debugPrint('DashboardNotifier: Auto-refreshing data');
          loadAllData();
        }
      },
    );
  }

  @override
  void dispose() {
    _autoRefreshTimer?.cancel();
    super.dispose();
  }
}

/// Provider for DashboardNotifier
final dashboardProvider =
    StateNotifierProvider<DashboardNotifier, DashboardState>((ref) {
  return DashboardNotifier(
    repository: ref.watch(dashboardRepositoryProvider),
  );
});

/// Provider for dashboard stats only
final dashboardStatsProvider = Provider<DashboardStats?>((ref) {
  return ref.watch(dashboardProvider).stats;
});

/// Provider for activity feed only
final activityFeedProvider = Provider<List<ActivityItem>>((ref) {
  return ref.watch(dashboardProvider).activity;
});

/// Provider for alerts only
final alertsProvider = Provider<List<Alert>>((ref) {
  return ref.watch(dashboardProvider).alerts;
});

/// Provider for critical alerts count
final criticalAlertsCountProvider = Provider<int>((ref) {
  return ref.watch(dashboardProvider).criticalAlertsCount;
});
