import 'dart:io';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

import 'tables/properties_table.dart';
import 'tables/buildings_table.dart';
import 'tables/units_table.dart';
import 'tables/tenants_table.dart';
import 'tables/leases_table.dart';
import 'tables/work_orders_table.dart';
import 'tables/rent_payments_table.dart';
import 'tables/support_tickets_table.dart';
import 'tables/iot_devices_table.dart';
import 'tables/sync_queue_table.dart';
import 'tables/sync_metadata_table.dart';

part 'app_database.g.dart';

/// Main application database using Drift for offline-first architecture
@DriftDatabase(tables: [
  PropertiesTable,
  BuildingsTable,
  UnitsTable,
  TenantsTable,
  LeasesTable,
  WorkOrdersTable,
  RentPaymentsTable,
  SupportTicketsTable,
  IoTDevicesTable,
  SyncQueueTable,
  SyncMetadataTable,
])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (Migrator m) async {
          await m.createAll();
        },
        onUpgrade: (Migrator m, int from, int to) async {
          // Future migrations will be handled here
        },
      );

  /// Clear all data from the database (for logout/reset)
  Future<void> clearAllData() async {
    await transaction(() async {
      // Clear entity tables
      await delete(propertiesTable).go();
      await delete(buildingsTable).go();
      await delete(unitsTable).go();
      await delete(tenantsTable).go();
      await delete(leasesTable).go();
      await delete(workOrdersTable).go();
      await delete(rentPaymentsTable).go();
      await delete(supportTicketsTable).go();
      await delete(ioTDevicesTable).go();

      // Clear sync tables
      await delete(syncQueueTable).go();
      await delete(syncMetadataTable).go();
    });
  }

  /// Get sync metadata for tracking last sync time
  Future<SyncMetadataTableData?> getSyncMetadata(String key) async {
    return (select(syncMetadataTable)
          ..where((tbl) => tbl.key.equals(key)))
        .getSingleOrNull();
  }

  /// Update or insert sync metadata
  Future<void> upsertSyncMetadata(String key, String value) async {
    await into(syncMetadataTable).insertOnConflictUpdate(
      SyncMetadataTableCompanion(
        key: Value(key),
        value: Value(value),
        updatedAt: Value(DateTime.now()),
      ),
    );
  }

  /// Get pending sync queue items
  Future<List<SyncQueueTableData>> getPendingSyncQueue() async {
    return (select(syncQueueTable)
          ..where((tbl) => tbl.isSynced.equals(false))
          ..orderBy([(tbl) => OrderingTerm.asc(tbl.timestamp)]))
        .get();
  }

  /// Add item to sync queue
  Future<int> addToSyncQueue({
    required String entityType,
    required String entityId,
    required String operation,
    required String jsonData,
    String? localId,
  }) async {
    return await into(syncQueueTable).insert(
      SyncQueueTableCompanion(
        entityType: Value(entityType),
        entityId: Value(entityId),
        operation: Value(operation),
        jsonData: Value(jsonData),
        localId: Value(localId),
        timestamp: Value(DateTime.now()),
        isSynced: const Value(false),
        retryCount: const Value(0),
      ),
    );
  }

  /// Mark sync queue item as synced
  Future<void> markSyncQueueItemSynced(int id, {String? serverEntityId}) async {
    await (update(syncQueueTable)..where((tbl) => tbl.id.equals(id))).write(
      SyncQueueTableCompanion(
        isSynced: const Value(true),
        syncedAt: Value(DateTime.now()),
        serverEntityId: Value(serverEntityId),
      ),
    );
  }

  /// Increment retry count for sync queue item
  Future<void> incrementSyncQueueRetry(int id, String error) async {
    final item = await (select(syncQueueTable)
          ..where((tbl) => tbl.id.equals(id)))
        .getSingleOrNull();

    if (item != null) {
      await (update(syncQueueTable)..where((tbl) => tbl.id.equals(id))).write(
        SyncQueueTableCompanion(
          retryCount: Value(item.retryCount + 1),
          lastError: Value(error),
        ),
      );
    }
  }

  /// Delete synced items older than a certain date
  Future<void> cleanupSyncedItems(DateTime olderThan) async {
    await (delete(syncQueueTable)
          ..where((tbl) =>
              tbl.isSynced.equals(true) &
              tbl.syncedAt.isSmallerThanValue(olderThan)))
        .go();
  }
}

/// Open database connection
LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'somni_property.db'));
    return NativeDatabase(file);
  });
}
