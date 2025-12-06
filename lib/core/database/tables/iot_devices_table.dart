import 'package:drift/drift.dart';

/// IoT Devices table for offline storage
@DataClassName('IoTDeviceTableData')
class IoTDevicesTable extends Table {
  TextColumn get id => text()();
  TextColumn get propertyId => text()();
  TextColumn get unitId => text().nullable()();
  TextColumn get name => text()();
  TextColumn get deviceType => text()();
  TextColumn get manufacturer => text().nullable()();
  TextColumn get model => text().nullable()();
  TextColumn get macAddress => text().nullable()();
  TextColumn get ipAddress => text().nullable()();
  TextColumn get status => text()();
  DateTimeColumn get lastSeen => dateTime().nullable()();
  TextColumn get firmwareVersion => text().nullable()();
  TextColumn get location => text().nullable()();
  TextColumn get configuration => text().nullable()(); // JSON as string
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  // Sync metadata
  IntColumn get version => integer().withDefault(const Constant(1))();
  TextColumn get lastModifiedBy => text().nullable()();
  BoolColumn get isDirty => boolean().withDefault(const Constant(false))();

  @override
  Set<Column> get primaryKey => {id};
}
