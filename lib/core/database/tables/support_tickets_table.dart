import 'package:drift/drift.dart';

/// Support Tickets table for offline storage
@DataClassName('SupportTicketTableData')
class SupportTicketsTable extends Table {
  TextColumn get id => text()();
  TextColumn get userId => text()();
  TextColumn get title => text()();
  TextColumn get description => text()();
  TextColumn get category => text()();
  TextColumn get priority => text()();
  TextColumn get status => text()();
  TextColumn get assignedTo => text().nullable()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();
  DateTimeColumn get resolvedAt => dateTime().nullable()();
  TextColumn get resolution => text().nullable()();
  TextColumn get attachments => text().nullable()(); // JSON array as string

  // Sync metadata
  IntColumn get version => integer().withDefault(const Constant(1))();
  TextColumn get lastModifiedBy => text().nullable()();
  BoolColumn get isDirty => boolean().withDefault(const Constant(false))();

  @override
  Set<Column> get primaryKey => {id};
}
