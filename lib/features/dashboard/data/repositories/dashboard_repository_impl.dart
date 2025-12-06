import 'package:dartz/dartz.dart';
import 'package:flutter/foundation.dart';
import 'package:somni_property/core/errors/exceptions.dart';
import 'package:somni_property/core/errors/failures.dart';
import 'package:somni_property/features/dashboard/data/datasources/dashboard_remote_datasource.dart';
import 'package:somni_property/features/dashboard/domain/entities/activity_item.dart';
import 'package:somni_property/features/dashboard/domain/entities/alert.dart';
import 'package:somni_property/features/dashboard/domain/entities/dashboard_stats.dart';
import 'package:somni_property/features/dashboard/domain/repositories/dashboard_repository.dart';

/// Implementation of DashboardRepository
class DashboardRepositoryImpl implements DashboardRepository {
  final DashboardRemoteDataSource remoteDataSource;

  DashboardRepositoryImpl({
    required this.remoteDataSource,
  });

  @override
  Future<Either<Failure, DashboardStats>> getStats() async {
    try {
      debugPrint('DashboardRepository: Getting stats');
      final stats = await remoteDataSource.getStats();
      return Right(stats);
    } on ServerException catch (e) {
      debugPrint('DashboardRepository: Server error - ${e.message}');
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      debugPrint('DashboardRepository: Network error - ${e.message}');
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      debugPrint('DashboardRepository: Unexpected error - $e');
      return Left(ServerFailure(message: 'Failed to fetch stats'));
    }
  }

  @override
  Future<Either<Failure, List<RevenueData>>> getRevenue({int months = 12}) async {
    try {
      debugPrint('DashboardRepository: Getting revenue data');
      final revenue = await remoteDataSource.getRevenue(months: months);
      return Right(revenue.cast<RevenueData>());
    } on ServerException catch (e) {
      debugPrint('DashboardRepository: Server error - ${e.message}');
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      debugPrint('DashboardRepository: Network error - ${e.message}');
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      debugPrint('DashboardRepository: Unexpected error - $e');
      return Left(ServerFailure(message: 'Failed to fetch revenue data'));
    }
  }

  @override
  Future<Either<Failure, OccupancyStats>> getOccupancy() async {
    try {
      debugPrint('DashboardRepository: Getting occupancy stats');
      final occupancy = await remoteDataSource.getOccupancy();
      return Right(occupancy);
    } on ServerException catch (e) {
      debugPrint('DashboardRepository: Server error - ${e.message}');
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      debugPrint('DashboardRepository: Network error - ${e.message}');
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      debugPrint('DashboardRepository: Unexpected error - $e');
      return Left(ServerFailure(message: 'Failed to fetch occupancy stats'));
    }
  }

  @override
  Future<Either<Failure, WorkOrderStats>> getWorkOrders() async {
    try {
      debugPrint('DashboardRepository: Getting work order stats');
      final workOrders = await remoteDataSource.getWorkOrders();
      return Right(workOrders);
    } on ServerException catch (e) {
      debugPrint('DashboardRepository: Server error - ${e.message}');
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      debugPrint('DashboardRepository: Network error - ${e.message}');
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      debugPrint('DashboardRepository: Unexpected error - $e');
      return Left(ServerFailure(message: 'Failed to fetch work order stats'));
    }
  }

  @override
  Future<Either<Failure, List<ActivityItem>>> getActivity({int limit = 20}) async {
    try {
      debugPrint('DashboardRepository: Getting activity feed');
      final activity = await remoteDataSource.getActivity(limit: limit);
      return Right(activity.cast<ActivityItem>());
    } on ServerException catch (e) {
      debugPrint('DashboardRepository: Server error - ${e.message}');
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      debugPrint('DashboardRepository: Network error - ${e.message}');
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      debugPrint('DashboardRepository: Unexpected error - $e');
      return Left(ServerFailure(message: 'Failed to fetch activity feed'));
    }
  }

  @override
  Future<Either<Failure, List<Alert>>> getAlerts() async {
    try {
      debugPrint('DashboardRepository: Getting alerts');
      final alerts = await remoteDataSource.getAlerts();
      return Right(alerts.cast<Alert>());
    } on ServerException catch (e) {
      debugPrint('DashboardRepository: Server error - ${e.message}');
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      debugPrint('DashboardRepository: Network error - ${e.message}');
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      debugPrint('DashboardRepository: Unexpected error - $e');
      return Left(ServerFailure(message: 'Failed to fetch alerts'));
    }
  }

  @override
  Future<Either<Failure, List<UpcomingEvent>>> getUpcoming({int days = 30}) async {
    try {
      debugPrint('DashboardRepository: Getting upcoming events');
      final events = await remoteDataSource.getUpcoming(days: days);
      return Right(events.cast<UpcomingEvent>());
    } on ServerException catch (e) {
      debugPrint('DashboardRepository: Server error - ${e.message}');
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      debugPrint('DashboardRepository: Network error - ${e.message}');
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      debugPrint('DashboardRepository: Unexpected error - $e');
      return Left(ServerFailure(message: 'Failed to fetch upcoming events'));
    }
  }

  @override
  Future<Either<Failure, void>> dismissAlert(String alertId) async {
    try {
      debugPrint('DashboardRepository: Dismissing alert $alertId');
      await remoteDataSource.dismissAlert(alertId);
      return const Right(null);
    } on ServerException catch (e) {
      debugPrint('DashboardRepository: Server error - ${e.message}');
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      debugPrint('DashboardRepository: Network error - ${e.message}');
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      debugPrint('DashboardRepository: Unexpected error - $e');
      return Left(ServerFailure(message: 'Failed to dismiss alert'));
    }
  }

  @override
  Future<Either<Failure, DashboardData>> getAllData() async {
    try {
      debugPrint('DashboardRepository: Getting all dashboard data');

      // Fetch all data in parallel for faster loading
      final results = await Future.wait([
        remoteDataSource.getStats(),
        remoteDataSource.getRevenue(months: 12),
        remoteDataSource.getOccupancy(),
        remoteDataSource.getWorkOrders(),
        remoteDataSource.getActivity(limit: 20),
        remoteDataSource.getAlerts(),
        remoteDataSource.getUpcoming(days: 30),
      ]);

      final dashboardData = DashboardData(
        stats: results[0] as DashboardStats,
        revenue: (results[1] as List).cast<RevenueData>(),
        occupancy: results[2] as OccupancyStats,
        workOrders: results[3] as WorkOrderStats,
        activity: (results[4] as List).cast<ActivityItem>(),
        alerts: (results[5] as List).cast<Alert>(),
        upcomingEvents: (results[6] as List).cast<UpcomingEvent>(),
      );

      debugPrint('DashboardRepository: Successfully fetched all dashboard data');
      return Right(dashboardData);
    } on ServerException catch (e) {
      debugPrint('DashboardRepository: Server error - ${e.message}');
      return Left(ServerFailure(message: e.message));
    } on NetworkException catch (e) {
      debugPrint('DashboardRepository: Network error - ${e.message}');
      return Left(NetworkFailure(message: e.message));
    } catch (e) {
      debugPrint('DashboardRepository: Unexpected error - $e');
      return Left(ServerFailure(message: 'Failed to fetch dashboard data'));
    }
  }
}
