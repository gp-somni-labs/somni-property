import 'package:dio/dio.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/work_orders/data/models/work_order_model.dart';
import 'package:somni_property/features/work_orders/domain/entities/work_order.dart';

/// Remote data source for work order API operations
abstract class WorkOrderRemoteDataSource {
  /// Get all work orders with optional filters
  Future<List<WorkOrderModel>> getWorkOrders({
    String? unitId,
    String? tenantId,
    String? assignedTo,
    WorkOrderStatus? status,
    WorkOrderPriority? priority,
    WorkOrderCategory? category,
  });

  /// Get a single work order by ID
  Future<WorkOrderModel> getWorkOrder(String id);

  /// Get work orders by status
  Future<List<WorkOrderModel>> getWorkOrdersByStatus(WorkOrderStatus status);

  /// Get work orders by priority
  Future<List<WorkOrderModel>> getWorkOrdersByPriority(WorkOrderPriority priority);

  /// Get open work orders
  Future<List<WorkOrderModel>> getOpenWorkOrders();

  /// Get work orders for a unit
  Future<List<WorkOrderModel>> getWorkOrdersForUnit(String unitId);

  /// Get work orders for an assignee
  Future<List<WorkOrderModel>> getWorkOrdersForAssignee(String assigneeId);

  /// Get urgent work orders
  Future<List<WorkOrderModel>> getUrgentWorkOrders();

  /// Create a new work order
  Future<WorkOrderModel> createWorkOrder(WorkOrderModel workOrder);

  /// Update a work order
  Future<WorkOrderModel> updateWorkOrder(WorkOrderModel workOrder);

  /// Assign work order
  Future<WorkOrderModel> assignWorkOrder(String workOrderId, String assigneeId);

  /// Update status
  Future<WorkOrderModel> updateStatus(String workOrderId, WorkOrderStatus status);

  /// Complete work order
  Future<WorkOrderModel> completeWorkOrder(
    String workOrderId,
    DateTime completedDate,
    double? actualCost,
    String? notes,
  );

  /// Cancel work order
  Future<WorkOrderModel> cancelWorkOrder(String workOrderId, String reason);

  /// Delete a work order
  Future<void> deleteWorkOrder(String id);
}

/// Implementation of WorkOrderRemoteDataSource using Dio
class WorkOrderRemoteDataSourceImpl implements WorkOrderRemoteDataSource {
  final ApiClient _apiClient;
  static const String _baseEndpoint = '/api/v1/work-orders';

  WorkOrderRemoteDataSourceImpl(this._apiClient);

  @override
  Future<List<WorkOrderModel>> getWorkOrders({
    String? unitId,
    String? tenantId,
    String? assignedTo,
    WorkOrderStatus? status,
    WorkOrderPriority? priority,
    WorkOrderCategory? category,
  }) async {
    final queryParams = <String, dynamic>{};
    if (unitId != null) queryParams['unit_id'] = unitId;
    if (tenantId != null) queryParams['tenant_id'] = tenantId;
    if (assignedTo != null) queryParams['assigned_to'] = assignedTo;
    if (status != null) queryParams['status'] = status.name;
    if (priority != null) queryParams['priority'] = priority.name;
    if (category != null) queryParams['category'] = category.name;

    final response = await _apiClient.get(
      _baseEndpoint,
      queryParameters: queryParams,
    );

    final data = response.data;
    if (data is List) {
      return data.map((json) => WorkOrderModel.fromJson(json)).toList();
    } else if (data is Map && data['work_orders'] != null) {
      return (data['work_orders'] as List)
          .map((json) => WorkOrderModel.fromJson(json))
          .toList();
    } else if (data is Map && data['data'] != null) {
      return (data['data'] as List)
          .map((json) => WorkOrderModel.fromJson(json))
          .toList();
    }

    return [];
  }

  @override
  Future<WorkOrderModel> getWorkOrder(String id) async {
    final response = await _apiClient.get('$_baseEndpoint/$id');
    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['work_order'] != null) {
        return WorkOrderModel.fromJson(data['work_order']);
      }
      return WorkOrderModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<List<WorkOrderModel>> getWorkOrdersByStatus(WorkOrderStatus status) async {
    return getWorkOrders(status: status);
  }

  @override
  Future<List<WorkOrderModel>> getWorkOrdersByPriority(WorkOrderPriority priority) async {
    return getWorkOrders(priority: priority);
  }

  @override
  Future<List<WorkOrderModel>> getOpenWorkOrders() async {
    final response = await _apiClient.get('$_baseEndpoint/open');
    final data = response.data;
    if (data is List) {
      return data.map((json) => WorkOrderModel.fromJson(json)).toList();
    } else if (data is Map && data['work_orders'] != null) {
      return (data['work_orders'] as List)
          .map((json) => WorkOrderModel.fromJson(json))
          .toList();
    }
    return [];
  }

  @override
  Future<List<WorkOrderModel>> getWorkOrdersForUnit(String unitId) async {
    return getWorkOrders(unitId: unitId);
  }

  @override
  Future<List<WorkOrderModel>> getWorkOrdersForAssignee(String assigneeId) async {
    return getWorkOrders(assignedTo: assigneeId);
  }

  @override
  Future<List<WorkOrderModel>> getUrgentWorkOrders() async {
    final response = await _apiClient.get('$_baseEndpoint/urgent');
    final data = response.data;
    if (data is List) {
      return data.map((json) => WorkOrderModel.fromJson(json)).toList();
    } else if (data is Map && data['work_orders'] != null) {
      return (data['work_orders'] as List)
          .map((json) => WorkOrderModel.fromJson(json))
          .toList();
    }
    return [];
  }

  @override
  Future<WorkOrderModel> createWorkOrder(WorkOrderModel workOrder) async {
    final response = await _apiClient.post(
      _baseEndpoint,
      data: workOrder.toJson(),
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['work_order'] != null) {
        return WorkOrderModel.fromJson(data['work_order']);
      }
      return WorkOrderModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<WorkOrderModel> updateWorkOrder(WorkOrderModel workOrder) async {
    final response = await _apiClient.put(
      '$_baseEndpoint/${workOrder.id}',
      data: workOrder.toJson(),
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['work_order'] != null) {
        return WorkOrderModel.fromJson(data['work_order']);
      }
      return WorkOrderModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<WorkOrderModel> assignWorkOrder(
      String workOrderId, String assigneeId) async {
    final response = await _apiClient.post(
      '$_baseEndpoint/$workOrderId/assign',
      data: {'assigned_to': assigneeId},
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['work_order'] != null) {
        return WorkOrderModel.fromJson(data['work_order']);
      }
      return WorkOrderModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<WorkOrderModel> updateStatus(
      String workOrderId, WorkOrderStatus status) async {
    final response = await _apiClient.patch(
      '$_baseEndpoint/$workOrderId/status',
      data: {'status': status.name},
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['work_order'] != null) {
        return WorkOrderModel.fromJson(data['work_order']);
      }
      return WorkOrderModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<WorkOrderModel> completeWorkOrder(
    String workOrderId,
    DateTime completedDate,
    double? actualCost,
    String? notes,
  ) async {
    final response = await _apiClient.post(
      '$_baseEndpoint/$workOrderId/complete',
      data: {
        'completed_date': completedDate.toIso8601String(),
        if (actualCost != null) 'actual_cost': actualCost,
        if (notes != null) 'notes': notes,
      },
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['work_order'] != null) {
        return WorkOrderModel.fromJson(data['work_order']);
      }
      return WorkOrderModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<WorkOrderModel> cancelWorkOrder(
      String workOrderId, String reason) async {
    final response = await _apiClient.post(
      '$_baseEndpoint/$workOrderId/cancel',
      data: {'reason': reason},
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['work_order'] != null) {
        return WorkOrderModel.fromJson(data['work_order']);
      }
      return WorkOrderModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<void> deleteWorkOrder(String id) async {
    await _apiClient.delete('$_baseEndpoint/$id');
  }
}
