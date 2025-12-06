import 'package:drift/drift.dart';

/// Sync Queue table for tracking pending changes to sync with server
@DataClassName('SyncQueueTableData')
class SyncQueueTable extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get entityType => text()(); // 'properties', 'tenants', 'work_orders', etc.
  TextColumn get entityId => text()(); // UUID of the entity
  TextColumn get operation => text()(); // 'CREATE', 'UPDATE', 'DELETE'
  TextColumn get jsonData => text()(); // Serialized entity data
  TextColumn get localId => text().nullable()(); // Temp ID for CREATE operations
  DateTimeColumn get timestamp => dateTime()(); // When change was made locally
  BoolColumn get isSynced => boolean().withDefault(const Constant(false))();
  DateTimeColumn get syncedAt => dateTime().nullable()();
  IntColumn get retryCount => integer().withDefault(const Constant(0))();
  TextColumn get lastError => text().nullable()();
  TextColumn get serverEntityId => text().nullable()(); // Server-assigned ID for CREATE operations

  @override
  Set<Column> get primaryKey => {id};
}
