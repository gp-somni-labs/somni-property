import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/dashboard/data/models/activity_item_model.dart';
import 'package:somni_property/features/dashboard/data/models/alert_model.dart';
import 'package:somni_property/features/dashboard/data/models/dashboard_stats_model.dart';

/// Remote data source for dashboard - connects to production backend
abstract class DashboardRemoteDataSource {
  /// Get overall dashboard statistics
  Future<DashboardStatsModel> getStats();

  /// Get revenue data for charts (last 12 months)
  Future<List<RevenueDataModel>> getRevenue({int months = 12});

  /// Get occupancy statistics
  Future<OccupancyStatsModel> getOccupancy();

  /// Get work order metrics
  Future<WorkOrderStatsModel> getWorkOrders();

  /// Get recent activity feed
  Future<List<ActivityItemModel>> getActivity({int limit = 20});

  /// Get urgent alerts
  Future<List<AlertModel>> getAlerts();

  /// Get upcoming events
  Future<List<UpcomingEventModel>> getUpcoming({int days = 30});

  /// Dismiss an alert
  Future<void> dismissAlert(String alertId);
}

/// Implementation connecting to production backend
class DashboardRemoteDataSourceImpl implements DashboardRemoteDataSource {
  final ApiClient apiClient;

  DashboardRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<DashboardStatsModel> getStats() async {
    try {
      debugPrint('DashboardRemoteDataSource: Fetching dashboard stats');

      final response = await apiClient.dio.get('/dashboard/stats');

      debugPrint(
          'DashboardRemoteDataSource: Received stats response: ${response.statusCode}');

      return DashboardStatsModel.fromJson(
          response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint('DashboardRemoteDataSource: Error fetching stats: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('DashboardRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to fetch dashboard stats: $e');
    }
  }

  @override
  Future<List<RevenueDataModel>> getRevenue({int months = 12}) async {
    try {
      debugPrint(
          'DashboardRemoteDataSource: Fetching revenue data (months: $months)');

      final response = await apiClient.dio.get(
        '/dashboard/revenue',
        queryParameters: {'months': months},
      );

      debugPrint(
          'DashboardRemoteDataSource: Received revenue response: ${response.statusCode}');

      // Backend returns list of revenue data points
      final data = response.data as List<dynamic>?;

      if (data == null || data.isEmpty) {
        debugPrint(
            'DashboardRemoteDataSource: No revenue data, returning empty list');
        return [];
      }

      final revenueData = data
          .map((json) => RevenueDataModel.fromJson(json as Map<String, dynamic>))
          .toList();

      debugPrint(
          'DashboardRemoteDataSource: Parsed ${revenueData.length} revenue data points');
      return revenueData;
    } on DioException catch (e) {
      debugPrint(
          'DashboardRemoteDataSource: Error fetching revenue: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('DashboardRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to fetch revenue data: $e');
    }
  }

  @override
  Future<OccupancyStatsModel> getOccupancy() async {
    try {
      debugPrint('DashboardRemoteDataSource: Fetching occupancy stats');

      final response = await apiClient.dio.get('/dashboard/occupancy');

      debugPrint(
          'DashboardRemoteDataSource: Received occupancy response: ${response.statusCode}');

      return OccupancyStatsModel.fromJson(
          response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint(
          'DashboardRemoteDataSource: Error fetching occupancy: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('DashboardRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to fetch occupancy stats: $e');
    }
  }

  @override
  Future<WorkOrderStatsModel> getWorkOrders() async {
    try {
      debugPrint('DashboardRemoteDataSource: Fetching work order stats');

      final response = await apiClient.dio.get('/dashboard/work-orders');

      debugPrint(
          'DashboardRemoteDataSource: Received work orders response: ${response.statusCode}');

      return WorkOrderStatsModel.fromJson(
          response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint(
          'DashboardRemoteDataSource: Error fetching work orders: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('DashboardRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to fetch work order stats: $e');
    }
  }

  @override
  Future<List<ActivityItemModel>> getActivity({int limit = 20}) async {
    try {
      debugPrint(
          'DashboardRemoteDataSource: Fetching activity feed (limit: $limit)');

      final response = await apiClient.dio.get(
        '/dashboard/activity',
        queryParameters: {'limit': limit},
      );

      debugPrint(
          'DashboardRemoteDataSource: Received activity response: ${response.statusCode}');

      // Backend returns list of activity items
      final data = response.data as List<dynamic>?;

      if (data == null || data.isEmpty) {
        debugPrint(
            'DashboardRemoteDataSource: No activity, returning empty list');
        return [];
      }

      final activities = data
          .map((json) =>
              ActivityItemModel.fromJson(json as Map<String, dynamic>))
          .toList();

      debugPrint(
          'DashboardRemoteDataSource: Parsed ${activities.length} activity items');
      return activities;
    } on DioException catch (e) {
      debugPrint(
          'DashboardRemoteDataSource: Error fetching activity: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('DashboardRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to fetch activity feed: $e');
    }
  }

  @override
  Future<List<AlertModel>> getAlerts() async {
    try {
      debugPrint('DashboardRemoteDataSource: Fetching alerts');

      final response = await apiClient.dio.get('/dashboard/alerts');

      debugPrint(
          'DashboardRemoteDataSource: Received alerts response: ${response.statusCode}');

      // Backend returns list of alerts
      final data = response.data as List<dynamic>?;

      if (data == null || data.isEmpty) {
        debugPrint('DashboardRemoteDataSource: No alerts, returning empty list');
        return [];
      }

      final alerts = data
          .map((json) => AlertModel.fromJson(json as Map<String, dynamic>))
          .toList();

      debugPrint('DashboardRemoteDataSource: Parsed ${alerts.length} alerts');
      return alerts;
    } on DioException catch (e) {
      debugPrint('DashboardRemoteDataSource: Error fetching alerts: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('DashboardRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to fetch alerts: $e');
    }
  }

  @override
  Future<List<UpcomingEventModel>> getUpcoming({int days = 30}) async {
    try {
      debugPrint(
          'DashboardRemoteDataSource: Fetching upcoming events (days: $days)');

      final response = await apiClient.dio.get(
        '/dashboard/upcoming',
        queryParameters: {'days': days},
      );

      debugPrint(
          'DashboardRemoteDataSource: Received upcoming events response: ${response.statusCode}');

      // Backend returns list of upcoming events
      final data = response.data as List<dynamic>?;

      if (data == null || data.isEmpty) {
        debugPrint(
            'DashboardRemoteDataSource: No upcoming events, returning empty list');
        return [];
      }

      final events = data
          .map((json) =>
              UpcomingEventModel.fromJson(json as Map<String, dynamic>))
          .toList();

      debugPrint(
          'DashboardRemoteDataSource: Parsed ${events.length} upcoming events');
      return events;
    } on DioException catch (e) {
      debugPrint(
          'DashboardRemoteDataSource: Error fetching upcoming events: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('DashboardRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to fetch upcoming events: $e');
    }
  }

  @override
  Future<void> dismissAlert(String alertId) async {
    try {
      debugPrint('DashboardRemoteDataSource: Dismissing alert $alertId');

      await apiClient.dio.post('/dashboard/alerts/$alertId/dismiss');

      debugPrint('DashboardRemoteDataSource: Alert dismissed successfully');
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        debugPrint('DashboardRemoteDataSource: Alert $alertId not found');
        throw const ServerException(message: 'Alert not found');
      }
      debugPrint(
          'DashboardRemoteDataSource: Error dismissing alert: ${e.message}');
      throw e.toAppException();
    } catch (e) {
      debugPrint('DashboardRemoteDataSource: Unexpected error: $e');
      throw ServerException(message: 'Failed to dismiss alert: $e');
    }
  }
}
