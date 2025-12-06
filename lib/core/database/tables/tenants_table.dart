import 'package:drift/drift.dart';

/// Tenants table for offline storage
@DataClassName('TenantTableData')
class TenantsTable extends Table {
  TextColumn get id => text()();
  TextColumn get firstName => text()();
  TextColumn get lastName => text()();
  TextColumn get email => text()();
  TextColumn get phone => text()();
  TextColumn get dateOfBirth => text().nullable()();
  TextColumn get emergencyContact => text().nullable()(); // JSON as string
  TextColumn get currentUnitId => text().nullable()();
  TextColumn get currentLeaseId => text().nullable()();
  TextColumn get status => text()(); // TenantStatus enum as string
  TextColumn get notes => text().nullable()();
  TextColumn get profileImageUrl => text().nullable()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  // Sync metadata
  IntColumn get version => integer().withDefault(const Constant(1))();
  TextColumn get lastModifiedBy => text().nullable()();
  BoolColumn get isDirty => boolean().withDefault(const Constant(false))();

  @override
  Set<Column> get primaryKey => {id};
}
