import 'package:drift/drift.dart';

/// Sync Metadata table for storing sync state information
@DataClassName('SyncMetadataTableData')
class SyncMetadataTable extends Table {
  TextColumn get key => text()(); // e.g., 'last_sync_timestamp', 'device_id', 'client_id'
  TextColumn get value => text()();
  DateTimeColumn get updatedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {key};
}
