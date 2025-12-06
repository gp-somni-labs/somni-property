import 'package:drift/drift.dart';

/// Buildings table for offline storage
@DataClassName('BuildingTableData')
class BuildingsTable extends Table {
  TextColumn get id => text()();
  TextColumn get propertyId => text()();
  TextColumn get name => text()();
  TextColumn get address => text().nullable()();
  IntColumn get floors => integer().nullable()();
  IntColumn get totalUnits => integer()();
  TextColumn get notes => text().nullable()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  // Sync metadata
  IntColumn get version => integer().withDefault(const Constant(1))();
  TextColumn get lastModifiedBy => text().nullable()();
  BoolColumn get isDirty => boolean().withDefault(const Constant(false))();

  @override
  Set<Column> get primaryKey => {id};
}
