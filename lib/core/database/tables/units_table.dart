import 'package:drift/drift.dart';

/// Units table for offline storage
@DataClassName('UnitTableData')
class UnitsTable extends Table {
  TextColumn get id => text()();
  TextColumn get propertyId => text()();
  TextColumn get buildingId => text().nullable()();
  TextColumn get unitNumber => text()();
  IntColumn get bedrooms => integer().nullable()();
  RealColumn get bathrooms => real().nullable()();
  RealColumn get squareFeet => real().nullable()();
  RealColumn get rentAmount => real()();
  TextColumn get status => text()(); // UnitStatus enum as string
  TextColumn get floor => text().nullable()();
  TextColumn get description => text().nullable()();
  TextColumn get amenities => text().nullable()(); // JSON array as string
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  // Sync metadata
  IntColumn get version => integer().withDefault(const Constant(1))();
  TextColumn get lastModifiedBy => text().nullable()();
  BoolColumn get isDirty => boolean().withDefault(const Constant(false))();

  @override
  Set<Column> get primaryKey => {id};
}
