import 'package:drift/drift.dart';

/// Properties table for offline storage
@DataClassName('PropertyTableData')
class PropertiesTable extends Table {
  TextColumn get id => text()();
  TextColumn get name => text()();
  TextColumn get address => text()();
  TextColumn get city => text()();
  TextColumn get state => text()();
  TextColumn get zipCode => text()();
  TextColumn get type => text()(); // PropertyType enum as string
  TextColumn get status => text()(); // PropertyStatus enum as string
  IntColumn get totalUnits => integer()();
  IntColumn get occupiedUnits => integer().withDefault(const Constant(0))();
  RealColumn get monthlyRevenue => real().nullable()();
  TextColumn get description => text().nullable()();
  TextColumn get imageUrl => text().nullable()();
  TextColumn get ownerId => text()();
  TextColumn get managerId => text().nullable()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  // Sync metadata
  IntColumn get version => integer().withDefault(const Constant(1))();
  TextColumn get lastModifiedBy => text().nullable()();
  BoolColumn get isDirty => boolean().withDefault(const Constant(false))(); // Local changes not synced

  @override
  Set<Column> get primaryKey => {id};
}
