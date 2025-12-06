import 'dart:convert';
import 'package:drift/drift.dart';
import 'package:logger/logger.dart';

import '../database/app_database.dart';
import 'sync_models.dart';

/// Handles applying sync changes to specific entity tables
class EntitySyncHandler {
  final AppDatabase _database;
  final Logger _logger;

  EntitySyncHandler({
    required AppDatabase database,
    required Logger logger,
  })  : _database = database,
        _logger = logger;

  /// Apply a sync change to the appropriate entity table
  Future<void> applyChange(SyncChange change) async {
    try {
      switch (change.entityType) {
        case 'properties':
          await _applyPropertyChange(change);
          break;
        case 'buildings':
          await _applyBuildingChange(change);
          break;
        case 'units':
          await _applyUnitChange(change);
          break;
        case 'tenants':
          await _applyTenantChange(change);
          break;
        case 'leases':
          await _applyLeaseChange(change);
          break;
        case 'work_orders':
          await _applyWorkOrderChange(change);
          break;
        case 'rent_payments':
          await _applyRentPaymentChange(change);
          break;
        case 'support_tickets':
          await _applySupportTicketChange(change);
          break;
        case 'iot_devices':
          await _applyIoTDeviceChange(change);
          break;
        default:
          _logger.w('Unknown entity type: ${change.entityType}');
      }
    } catch (e, stackTrace) {
      _logger.e('Error applying change to ${change.entityType}', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Update entity version in database
  Future<void> updateEntityVersion(String entityType, String entityId, int version) async {
    switch (entityType) {
      case 'properties':
        await (_database.update(_database.propertiesTable)
              ..where((tbl) => tbl.id.equals(entityId)))
            .write(PropertiesTableCompanion(version: Value(version)));
        break;
      case 'tenants':
        await (_database.update(_database.tenantsTable)
              ..where((tbl) => tbl.id.equals(entityId)))
            .write(TenantsTableCompanion(version: Value(version)));
        break;
      case 'leases':
        await (_database.update(_database.leasesTable)
              ..where((tbl) => tbl.id.equals(entityId)))
            .write(LeasesTableCompanion(version: Value(version)));
        break;
      case 'work_orders':
        await (_database.update(_database.workOrdersTable)
              ..where((tbl) => tbl.id.equals(entityId)))
            .write(WorkOrdersTableCompanion(version: Value(version)));
        break;
      // Add other entity types as needed
    }
  }

  // Property changes
  Future<void> _applyPropertyChange(SyncChange change) async {
    if (change.operation == 'DELETE') {
      await (_database.delete(_database.propertiesTable)
            ..where((tbl) => tbl.id.equals(change.entityId!)))
          .go();
    } else {
      final data = change.data!;
      final companion = PropertiesTableCompanion(
        id: Value(data['id'] as String),
        name: Value(data['name'] as String),
        address: Value(data['address'] as String),
        city: Value(data['city'] as String),
        state: Value(data['state'] as String),
        zipCode: Value(data['zip_code'] as String),
        type: Value(data['type'] as String),
        status: Value(data['status'] as String),
        totalUnits: Value(data['total_units'] as int),
        occupiedUnits: Value(data['occupied_units'] as int? ?? 0),
        monthlyRevenue: Value(data['monthly_revenue'] as double?),
        description: Value(data['description'] as String?),
        imageUrl: Value(data['image_url'] as String?),
        ownerId: Value(data['owner_id'] as String),
        managerId: Value(data['manager_id'] as String?),
        createdAt: Value(DateTime.parse(data['created_at'] as String)),
        updatedAt: Value(DateTime.parse(data['updated_at'] as String)),
        version: Value(data['version'] as int? ?? 1),
        lastModifiedBy: Value(data['last_modified_by'] as String?),
        isDirty: const Value(false),
      );

      await _database.into(_database.propertiesTable).insertOnConflictUpdate(companion);
    }
  }

  // Building changes
  Future<void> _applyBuildingChange(SyncChange change) async {
    if (change.operation == 'DELETE') {
      await (_database.delete(_database.buildingsTable)
            ..where((tbl) => tbl.id.equals(change.entityId!)))
          .go();
    } else {
      final data = change.data!;
      final companion = BuildingsTableCompanion(
        id: Value(data['id'] as String),
        propertyId: Value(data['property_id'] as String),
        name: Value(data['name'] as String),
        address: Value(data['address'] as String?),
        floors: Value(data['floors'] as int?),
        totalUnits: Value(data['total_units'] as int),
        notes: Value(data['notes'] as String?),
        createdAt: Value(DateTime.parse(data['created_at'] as String)),
        updatedAt: Value(DateTime.parse(data['updated_at'] as String)),
        version: Value(data['version'] as int? ?? 1),
        isDirty: const Value(false),
      );

      await _database.into(_database.buildingsTable).insertOnConflictUpdate(companion);
    }
  }

  // Unit changes
  Future<void> _applyUnitChange(SyncChange change) async {
    if (change.operation == 'DELETE') {
      await (_database.delete(_database.unitsTable)
            ..where((tbl) => tbl.id.equals(change.entityId!)))
          .go();
    } else {
      final data = change.data!;
      final companion = UnitsTableCompanion(
        id: Value(data['id'] as String),
        propertyId: Value(data['property_id'] as String),
        buildingId: Value(data['building_id'] as String?),
        unitNumber: Value(data['unit_number'] as String),
        bedrooms: Value(data['bedrooms'] as int?),
        bathrooms: Value(data['bathrooms'] as double?),
        squareFeet: Value(data['square_feet'] as double?),
        rentAmount: Value(data['rent_amount'] as double),
        status: Value(data['status'] as String),
        floor: Value(data['floor'] as String?),
        description: Value(data['description'] as String?),
        amenities: Value(data['amenities'] != null ? jsonEncode(data['amenities']) : null),
        createdAt: Value(DateTime.parse(data['created_at'] as String)),
        updatedAt: Value(DateTime.parse(data['updated_at'] as String)),
        version: Value(data['version'] as int? ?? 1),
        isDirty: const Value(false),
      );

      await _database.into(_database.unitsTable).insertOnConflictUpdate(companion);
    }
  }

  // Tenant changes
  Future<void> _applyTenantChange(SyncChange change) async {
    if (change.operation == 'DELETE') {
      await (_database.delete(_database.tenantsTable)
            ..where((tbl) => tbl.id.equals(change.entityId!)))
          .go();
    } else {
      final data = change.data!;
      final companion = TenantsTableCompanion(
        id: Value(data['id'] as String),
        firstName: Value(data['first_name'] as String),
        lastName: Value(data['last_name'] as String),
        email: Value(data['email'] as String),
        phone: Value(data['phone'] as String),
        dateOfBirth: Value(data['date_of_birth'] as String?),
        emergencyContact: Value(
            data['emergency_contact'] != null ? jsonEncode(data['emergency_contact']) : null),
        currentUnitId: Value(data['current_unit_id'] as String?),
        currentLeaseId: Value(data['current_lease_id'] as String?),
        status: Value(data['status'] as String),
        notes: Value(data['notes'] as String?),
        profileImageUrl: Value(data['profile_image_url'] as String?),
        createdAt: Value(DateTime.parse(data['created_at'] as String)),
        updatedAt: Value(DateTime.parse(data['updated_at'] as String)),
        version: Value(data['version'] as int? ?? 1),
        isDirty: const Value(false),
      );

      await _database.into(_database.tenantsTable).insertOnConflictUpdate(companion);
    }
  }

  // Lease changes
  Future<void> _applyLeaseChange(SyncChange change) async {
    if (change.operation == 'DELETE') {
      await (_database.delete(_database.leasesTable)
            ..where((tbl) => tbl.id.equals(change.entityId!)))
          .go();
    } else {
      final data = change.data!;
      final companion = LeasesTableCompanion(
        id: Value(data['id'] as String),
        propertyId: Value(data['property_id'] as String),
        unitId: Value(data['unit_id'] as String),
        tenantId: Value(data['tenant_id'] as String),
        startDate: Value(DateTime.parse(data['start_date'] as String)),
        endDate: Value(DateTime.parse(data['end_date'] as String)),
        monthlyRent: Value(data['monthly_rent'] as double),
        securityDeposit: Value(data['security_deposit'] as double),
        status: Value(data['status'] as String),
        type: Value(data['type'] as String),
        termMonths: Value(data['term_months'] as int),
        moveInDate: Value(
            data['move_in_date'] != null ? DateTime.parse(data['move_in_date'] as String) : null),
        moveOutDate: Value(data['move_out_date'] != null
            ? DateTime.parse(data['move_out_date'] as String)
            : null),
        renewalStatus: Value(data['renewal_status'] as String?),
        autoRenew: Value(data['auto_renew'] as bool? ?? false),
        terminationReason: Value(data['termination_reason'] as String?),
        terms: Value(data['terms'] as String?),
        specialConditions: Value(
            data['special_conditions'] != null ? jsonEncode(data['special_conditions']) : null),
        notes: Value(data['notes'] as String?),
        attachmentUrls: Value(
            data['attachment_urls'] != null ? jsonEncode(data['attachment_urls']) : null),
        createdAt: Value(DateTime.parse(data['created_at'] as String)),
        updatedAt: Value(DateTime.parse(data['updated_at'] as String)),
        version: Value(data['version'] as int? ?? 1),
        isDirty: const Value(false),
      );

      await _database.into(_database.leasesTable).insertOnConflictUpdate(companion);
    }
  }

  // Work Order changes
  Future<void> _applyWorkOrderChange(SyncChange change) async {
    if (change.operation == 'DELETE') {
      await (_database.delete(_database.workOrdersTable)
            ..where((tbl) => tbl.id.equals(change.entityId!)))
          .go();
    } else {
      final data = change.data!;
      final companion = WorkOrdersTableCompanion(
        id: Value(data['id'] as String),
        unitId: Value(data['unit_id'] as String),
        tenantId: Value(data['tenant_id'] as String?),
        title: Value(data['title'] as String),
        description: Value(data['description'] as String),
        category: Value(data['category'] as String),
        priority: Value(data['priority'] as String),
        status: Value(data['status'] as String),
        createdAt: Value(DateTime.parse(data['created_at'] as String)),
        updatedAt: Value(DateTime.parse(data['updated_at'] as String)),
        scheduledDate: Value(data['scheduled_date'] != null
            ? DateTime.parse(data['scheduled_date'] as String)
            : null),
        completedDate: Value(data['completed_date'] != null
            ? DateTime.parse(data['completed_date'] as String)
            : null),
        assignedTo: Value(data['assigned_to'] as String?),
        notes: Value(data['notes'] as String?),
        estimatedCost: Value(data['estimated_cost'] as double?),
        actualCost: Value(data['actual_cost'] as double?),
        attachments: Value(data['attachments'] != null ? jsonEncode(data['attachments']) : null),
        version: Value(data['version'] as int? ?? 1),
        isDirty: const Value(false),
      );

      await _database.into(_database.workOrdersTable).insertOnConflictUpdate(companion);
    }
  }

  // Rent Payment changes
  Future<void> _applyRentPaymentChange(SyncChange change) async {
    if (change.operation == 'DELETE') {
      await (_database.delete(_database.rentPaymentsTable)
            ..where((tbl) => tbl.id.equals(change.entityId!)))
          .go();
    } else {
      final data = change.data!;
      final companion = RentPaymentsTableCompanion(
        id: Value(data['id'] as String),
        leaseId: Value(data['lease_id'] as String),
        tenantId: Value(data['tenant_id'] as String),
        amount: Value(data['amount'] as double),
        dueDate: Value(DateTime.parse(data['due_date'] as String)),
        paidDate: Value(
            data['paid_date'] != null ? DateTime.parse(data['paid_date'] as String) : null),
        status: Value(data['status'] as String),
        paymentMethod: Value(data['payment_method'] as String?),
        transactionId: Value(data['transaction_id'] as String?),
        notes: Value(data['notes'] as String?),
        lateFee: Value(data['late_fee'] as double?),
        createdAt: Value(DateTime.parse(data['created_at'] as String)),
        updatedAt: Value(DateTime.parse(data['updated_at'] as String)),
        version: Value(data['version'] as int? ?? 1),
        isDirty: const Value(false),
      );

      await _database.into(_database.rentPaymentsTable).insertOnConflictUpdate(companion);
    }
  }

  // Support Ticket changes
  Future<void> _applySupportTicketChange(SyncChange change) async {
    if (change.operation == 'DELETE') {
      await (_database.delete(_database.supportTicketsTable)
            ..where((tbl) => tbl.id.equals(change.entityId!)))
          .go();
    } else {
      final data = change.data!;
      final companion = SupportTicketsTableCompanion(
        id: Value(data['id'] as String),
        userId: Value(data['user_id'] as String),
        title: Value(data['title'] as String),
        description: Value(data['description'] as String),
        category: Value(data['category'] as String),
        priority: Value(data['priority'] as String),
        status: Value(data['status'] as String),
        assignedTo: Value(data['assigned_to'] as String?),
        createdAt: Value(DateTime.parse(data['created_at'] as String)),
        updatedAt: Value(DateTime.parse(data['updated_at'] as String)),
        resolvedAt: Value(
            data['resolved_at'] != null ? DateTime.parse(data['resolved_at'] as String) : null),
        resolution: Value(data['resolution'] as String?),
        attachments: Value(data['attachments'] != null ? jsonEncode(data['attachments']) : null),
        version: Value(data['version'] as int? ?? 1),
        isDirty: const Value(false),
      );

      await _database.into(_database.supportTicketsTable).insertOnConflictUpdate(companion);
    }
  }

  // IoT Device changes
  Future<void> _applyIoTDeviceChange(SyncChange change) async {
    if (change.operation == 'DELETE') {
      await (_database.delete(_database.ioTDevicesTable)
            ..where((tbl) => tbl.id.equals(change.entityId!)))
          .go();
    } else {
      final data = change.data!;
      final companion = IoTDevicesTableCompanion(
        id: Value(data['id'] as String),
        propertyId: Value(data['property_id'] as String),
        unitId: Value(data['unit_id'] as String?),
        name: Value(data['name'] as String),
        deviceType: Value(data['device_type'] as String),
        manufacturer: Value(data['manufacturer'] as String?),
        model: Value(data['model'] as String?),
        macAddress: Value(data['mac_address'] as String?),
        ipAddress: Value(data['ip_address'] as String?),
        status: Value(data['status'] as String),
        lastSeen: Value(
            data['last_seen'] != null ? DateTime.parse(data['last_seen'] as String) : null),
        firmwareVersion: Value(data['firmware_version'] as String?),
        location: Value(data['location'] as String?),
        configuration:
            Value(data['configuration'] != null ? jsonEncode(data['configuration']) : null),
        createdAt: Value(DateTime.parse(data['created_at'] as String)),
        updatedAt: Value(DateTime.parse(data['updated_at'] as String)),
        version: Value(data['version'] as int? ?? 1),
        isDirty: const Value(false),
      );

      await _database.into(_database.ioTDevicesTable).insertOnConflictUpdate(companion);
    }
  }
}
