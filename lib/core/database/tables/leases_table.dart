import 'package:drift/drift.dart';

/// Leases table for offline storage
@DataClassName('LeaseTableData')
class LeasesTable extends Table {
  TextColumn get id => text()();
  TextColumn get propertyId => text()();
  TextColumn get unitId => text()();
  TextColumn get tenantId => text()();
  DateTimeColumn get startDate => dateTime()();
  DateTimeColumn get endDate => dateTime()();
  RealColumn get monthlyRent => real()();
  RealColumn get securityDeposit => real()();
  TextColumn get status => text()(); // LeaseStatus enum as string
  TextColumn get type => text()(); // LeaseType enum as string
  IntColumn get termMonths => integer()();
  DateTimeColumn get moveInDate => dateTime().nullable()();
  DateTimeColumn get moveOutDate => dateTime().nullable()();
  TextColumn get renewalStatus => text().nullable()();
  BoolColumn get autoRenew => boolean().withDefault(const Constant(false))();
  TextColumn get terminationReason => text().nullable()();
  TextColumn get terms => text().nullable()();
  TextColumn get specialConditions => text().nullable()(); // JSON array as string
  TextColumn get notes => text().nullable()();
  TextColumn get attachmentUrls => text().nullable()(); // JSON array as string
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  // Sync metadata
  IntColumn get version => integer().withDefault(const Constant(1))();
  TextColumn get lastModifiedBy => text().nullable()();
  BoolColumn get isDirty => boolean().withDefault(const Constant(false))();

  @override
  Set<Column> get primaryKey => {id};
}
