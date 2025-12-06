import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/error/failures.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/work_orders/data/datasources/work_order_remote_datasource.dart';
import 'package:somni_property/features/work_orders/data/models/work_order_model.dart';
import 'package:somni_property/features/work_orders/domain/entities/work_order.dart';
import 'package:somni_property/features/work_orders/domain/repositories/work_order_repository.dart';

/// Provider for work order repository
final workOrderRepositoryProvider = Provider<WorkOrderRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final dataSource = WorkOrderRemoteDataSourceImpl(apiClient);
  return WorkOrderRepositoryImpl(dataSource);
});

/// Implementation of WorkOrderRepository
class WorkOrderRepositoryImpl implements WorkOrderRepository {
  final WorkOrderRemoteDataSource _dataSource;

  WorkOrderRepositoryImpl(this._dataSource);

  @override
  Future<Either<Failure, List<WorkOrder>>> getWorkOrders({
    String? unitId,
    String? tenantId,
    String? assignedTo,
    WorkOrderStatus? status,
    WorkOrderPriority? priority,
    WorkOrderCategory? category,
  }) async {
    try {
      final workOrders = await _dataSource.getWorkOrders(
        unitId: unitId,
        tenantId: tenantId,
        assignedTo: assignedTo,
        status: status,
        priority: priority,
        category: category,
      );
      return Right(workOrders.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, WorkOrder>> getWorkOrder(String id) async {
    try {
      final workOrder = await _dataSource.getWorkOrder(id);
      return Right(workOrder.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<WorkOrder>>> getWorkOrdersByStatus(
      WorkOrderStatus status) async {
    try {
      final workOrders = await _dataSource.getWorkOrdersByStatus(status);
      return Right(workOrders.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<WorkOrder>>> getWorkOrdersByPriority(
      WorkOrderPriority priority) async {
    try {
      final workOrders = await _dataSource.getWorkOrdersByPriority(priority);
      return Right(workOrders.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<WorkOrder>>> getOpenWorkOrders() async {
    try {
      final workOrders = await _dataSource.getOpenWorkOrders();
      return Right(workOrders.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<WorkOrder>>> getWorkOrdersForUnit(
      String unitId) async {
    try {
      final workOrders = await _dataSource.getWorkOrdersForUnit(unitId);
      return Right(workOrders.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<WorkOrder>>> getWorkOrdersForAssignee(
      String assigneeId) async {
    try {
      final workOrders = await _dataSource.getWorkOrdersForAssignee(assigneeId);
      return Right(workOrders.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<WorkOrder>>> getUrgentWorkOrders() async {
    try {
      final workOrders = await _dataSource.getUrgentWorkOrders();
      return Right(workOrders.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, WorkOrder>> createWorkOrder(WorkOrder workOrder) async {
    try {
      final model = WorkOrderModel.fromEntity(workOrder);
      final created = await _dataSource.createWorkOrder(model);
      return Right(created.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, WorkOrder>> updateWorkOrder(WorkOrder workOrder) async {
    try {
      final model = WorkOrderModel.fromEntity(workOrder);
      final updated = await _dataSource.updateWorkOrder(model);
      return Right(updated.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, WorkOrder>> assignWorkOrder(
      String workOrderId, String assigneeId) async {
    try {
      final updated = await _dataSource.assignWorkOrder(workOrderId, assigneeId);
      return Right(updated.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, WorkOrder>> updateStatus(
      String workOrderId, WorkOrderStatus status) async {
    try {
      final updated = await _dataSource.updateStatus(workOrderId, status);
      return Right(updated.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, WorkOrder>> completeWorkOrder(
    String workOrderId,
    DateTime completedDate,
    double? actualCost,
    String? notes,
  ) async {
    try {
      final updated = await _dataSource.completeWorkOrder(
        workOrderId,
        completedDate,
        actualCost,
        notes,
      );
      return Right(updated.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, WorkOrder>> cancelWorkOrder(
      String workOrderId, String reason) async {
    try {
      final updated = await _dataSource.cancelWorkOrder(workOrderId, reason);
      return Right(updated.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> deleteWorkOrder(String id) async {
    try {
      await _dataSource.deleteWorkOrder(id);
      return const Right(null);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  Failure _handleDioError(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return const NetworkFailure(message: 'Connection timeout');
      case DioExceptionType.connectionError:
        return const NetworkFailure(message: 'No internet connection');
      case DioExceptionType.badResponse:
        final statusCode = e.response?.statusCode;
        final message = e.response?.data?['message']?.toString() ??
            e.response?.data?['error']?.toString() ??
            'Server error';
        if (statusCode == 401) {
          return AuthFailure(message: message);
        } else if (statusCode == 404) {
          return NotFoundFailure(message: message);
        } else if (statusCode == 422) {
          return ValidationFailure(message: message);
        }
        return ServerFailure(message: message);
      default:
        return ServerFailure(message: e.message ?? 'Unknown error');
    }
  }
}
