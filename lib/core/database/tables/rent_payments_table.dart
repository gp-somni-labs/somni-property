import 'package:drift/drift.dart';

/// Rent Payments table for offline storage
@DataClassName('RentPaymentTableData')
class RentPaymentsTable extends Table {
  TextColumn get id => text()();
  TextColumn get leaseId => text()();
  TextColumn get tenantId => text()();
  RealColumn get amount => real()();
  DateTimeColumn get dueDate => dateTime()();
  DateTimeColumn get paidDate => dateTime().nullable()();
  TextColumn get status => text()(); // PaymentStatus enum as string
  TextColumn get paymentMethod => text().nullable()();
  TextColumn get transactionId => text().nullable()();
  TextColumn get notes => text().nullable()();
  RealColumn get lateFee => real().nullable()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  // Sync metadata
  IntColumn get version => integer().withDefault(const Constant(1))();
  TextColumn get lastModifiedBy => text().nullable()();
  BoolColumn get isDirty => boolean().withDefault(const Constant(false))();

  @override
  Set<Column> get primaryKey => {id};
}
