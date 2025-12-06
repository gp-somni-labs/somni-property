import 'package:drift/drift.dart';

/// Work Orders table for offline storage
@DataClassName('WorkOrderTableData')
class WorkOrdersTable extends Table {
  TextColumn get id => text()();
  TextColumn get unitId => text()();
  TextColumn get tenantId => text().nullable()();
  TextColumn get title => text()();
  TextColumn get description => text()();
  TextColumn get category => text()(); // WorkOrderCategory enum as string
  TextColumn get priority => text()(); // WorkOrderPriority enum as string
  TextColumn get status => text()(); // WorkOrderStatus enum as string
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();
  DateTimeColumn get scheduledDate => dateTime().nullable()();
  DateTimeColumn get completedDate => dateTime().nullable()();
  TextColumn get assignedTo => text().nullable()();
  TextColumn get notes => text().nullable()();
  RealColumn get estimatedCost => real().nullable()();
  RealColumn get actualCost => real().nullable()();
  TextColumn get attachments => text().nullable()(); // JSON array as string

  // Sync metadata
  IntColumn get version => integer().withDefault(const Constant(1))();
  TextColumn get lastModifiedBy => text().nullable()();
  BoolColumn get isDirty => boolean().withDefault(const Constant(false))();

  @override
  Set<Column> get primaryKey => {id};
}
