import 'dart:convert';
import 'package:uuid/uuid.dart';
import '../../domain/entities/work_order.dart';
import '../../domain/repositories/work_order_repository.dart';
import '../../../../core/database/app_database.dart';
import '../../../../core/sync/connectivity_sync_service.dart';
import 'package:drift/drift.dart';

/// Example of offline-first repository implementation for Work Orders
/// This demonstrates the pattern for modifying repositories to support offline sync
class WorkOrderRepositoryOfflineExample implements WorkOrderRepository {
  final AppDatabase _database;
  final ConnectivitySyncService _connectivityService;

  WorkOrderRepositoryOfflineExample({
    required AppDatabase database,
    required ConnectivitySyncService connectivityService,
  })  : _database = database,
        _connectivityService = connectivityService;

  /// Get all work orders (offline-first)
  @override
  Future<List<WorkOrder>> getWorkOrders() async {
    // ALWAYS read from local database first (fast, works offline)
    final localData = await _database.select(_database.workOrdersTable).get();
    final workOrders = localData.map(_mapToEntity).toList();

    // If online, trigger background sync to get latest data
    if (_connectivityService.isOnline && !_connectivityService.isSyncing) {
      // Non-blocking: trigger sync in background
      _connectivityService.manualSync().then((_) {
        // Optionally: Notify UI to refresh data via stream/notifier
      }).catchError((error) {
        // Log error but don't fail the read operation
        print('Background sync failed: $error');
      });
    }

    return workOrders;
  }

  /// Get work order by ID (offline-first)
  @override
  Future<WorkOrder?> getWorkOrderById(String id) async {
    final data = await (_database.select(_database.workOrdersTable)
          ..where((tbl) => tbl.id.equals(id)))
        .getSingleOrNull();

    return data != null ? _mapToEntity(data) : null;
  }

  /// Create work order (queue for sync)
  @override
  Future<WorkOrder> createWorkOrder(WorkOrder workOrder) async {
    // 1. Insert into local database immediately
    final companion = _mapToCompanion(workOrder, isNew: true);
    await _database.into(_database.workOrdersTable).insert(companion);

    // 2. Add to sync queue for upload
    await _database.addToSyncQueue(
      entityType: 'work_orders',
      entityId: workOrder.id,
      operation: 'CREATE',
      jsonData: jsonEncode(_mapToJson(workOrder)),
      localId: 'temp-${workOrder.id}', // Temp ID for tracking
    );

    // 3. If online, trigger sync immediately
    if (_connectivityService.isOnline) {
      _connectivityService.manualSync().catchError((error) {
        // Sync will retry later if fails
        print('Immediate sync failed: $error');
      });
    }

    return workOrder;
  }

  /// Update work order (queue for sync)
  @override
  Future<WorkOrder> updateWorkOrder(WorkOrder workOrder) async {
    // 1. Update local database immediately
    final companion = _mapToCompanion(workOrder, isDirty: true);
    await (_database.update(_database.workOrdersTable)
          ..where((tbl) => tbl.id.equals(workOrder.id)))
        .write(companion);

    // 2. Add to sync queue for upload
    await _database.addToSyncQueue(
      entityType: 'work_orders',
      entityId: workOrder.id,
      operation: 'UPDATE',
      jsonData: jsonEncode(_mapToJson(workOrder)),
    );

    // 3. If online, trigger sync immediately
    if (_connectivityService.isOnline) {
      _connectivityService.manualSync().catchError((error) {
        print('Immediate sync failed: $error');
      });
    }

    return workOrder;
  }

  /// Delete work order (queue for sync)
  @override
  Future<void> deleteWorkOrder(String id) async {
    // 1. Delete from local database immediately
    await (_database.delete(_database.workOrdersTable)
          ..where((tbl) => tbl.id.equals(id)))
        .go();

    // 2. Add to sync queue for server deletion
    await _database.addToSyncQueue(
      entityType: 'work_orders',
      entityId: id,
      operation: 'DELETE',
      jsonData: jsonEncode({'id': id}), // Minimal data for DELETE
    );

    // 3. If online, trigger sync immediately
    if (_connectivityService.isOnline) {
      _connectivityService.manualSync().catchError((error) {
        print('Immediate sync failed: $error');
      });
    }
  }

  /// Get work orders by status (offline-first)
  @override
  Future<List<WorkOrder>> getWorkOrdersByStatus(WorkOrderStatus status) async {
    final statusString = status.name;
    final data = await (_database.select(_database.workOrdersTable)
          ..where((tbl) => tbl.status.equals(statusString)))
        .get();

    return data.map(_mapToEntity).toList();
  }

  /// Get work orders by unit ID (offline-first)
  @override
  Future<List<WorkOrder>> getWorkOrdersByUnitId(String unitId) async {
    final data = await (_database.select(_database.workOrdersTable)
          ..where((tbl) => tbl.unitId.equals(unitId)))
        .get();

    return data.map(_mapToEntity).toList();
  }

  /// Map database row to domain entity
  WorkOrder _mapToEntity(WorkOrderTableData data) {
    return WorkOrder(
      id: data.id,
      unitId: data.unitId,
      tenantId: data.tenantId,
      title: data.title,
      description: data.description,
      category: WorkOrderCategory.fromString(data.category),
      priority: WorkOrderPriority.fromString(data.priority),
      status: WorkOrderStatus.fromString(data.status),
      createdAt: data.createdAt,
      updatedAt: data.updatedAt,
      scheduledDate: data.scheduledDate,
      completedDate: data.completedDate,
      assignedTo: data.assignedTo,
      notes: data.notes,
      estimatedCost: data.estimatedCost,
      actualCost: data.actualCost,
      attachments: data.attachments != null
          ? List<String>.from(jsonDecode(data.attachments!))
          : null,
    );
  }

  /// Map domain entity to database companion
  WorkOrdersTableCompanion _mapToCompanion(WorkOrder workOrder, {
    bool isNew = false,
    bool isDirty = false,
  }) {
    return WorkOrdersTableCompanion(
      id: Value(workOrder.id),
      unitId: Value(workOrder.unitId),
      tenantId: Value(workOrder.tenantId),
      title: Value(workOrder.title),
      description: Value(workOrder.description),
      category: Value(workOrder.category.name),
      priority: Value(workOrder.priority.name),
      status: Value(workOrder.status.name),
      createdAt: Value(workOrder.createdAt),
      updatedAt: Value(workOrder.updatedAt),
      scheduledDate: Value(workOrder.scheduledDate),
      completedDate: Value(workOrder.completedDate),
      assignedTo: Value(workOrder.assignedTo),
      notes: Value(workOrder.notes),
      estimatedCost: Value(workOrder.estimatedCost),
      actualCost: Value(workOrder.actualCost),
      attachments: Value(
        workOrder.attachments != null ? jsonEncode(workOrder.attachments) : null
      ),
      version: Value(isNew ? 1 : (workOrder as dynamic).version ?? 1),
      isDirty: Value(isDirty || isNew),
    );
  }

  /// Map domain entity to JSON for sync queue
  Map<String, dynamic> _mapToJson(WorkOrder workOrder) {
    return {
      'id': workOrder.id,
      'unit_id': workOrder.unitId,
      'tenant_id': workOrder.tenantId,
      'title': workOrder.title,
      'description': workOrder.description,
      'category': workOrder.category.name,
      'priority': workOrder.priority.name,
      'status': workOrder.status.name,
      'created_at': workOrder.createdAt.toIso8601String(),
      'updated_at': workOrder.updatedAt.toIso8601String(),
      'scheduled_date': workOrder.scheduledDate?.toIso8601String(),
      'completed_date': workOrder.completedDate?.toIso8601String(),
      'assigned_to': workOrder.assignedTo,
      'notes': workOrder.notes,
      'estimated_cost': workOrder.estimatedCost,
      'actual_cost': workOrder.actualCost,
      'attachments': workOrder.attachments,
    };
  }
}
