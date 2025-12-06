# SomniProperty Database Schema for Flutter

> **Version**: 1.0.0
> **Last Updated**: 2025-12-04
> **Purpose**: Complete database schema documentation for Flutter data layer migration

---

## Table of Contents

1. [Overview](#overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Core Entities](#core-entities)
4. [Flutter Data Models](#flutter-data-models)
5. [SQLite Local Schema](#sqlite-local-schema)
6. [Sync Strategy](#sync-strategy)
7. [API Endpoints Reference](#api-endpoints-reference)

---

## Overview

SomniProperty is a property management application that handles:
- **Properties**: Real estate assets (apartments, houses, commercial)
- **Units**: Individual rental units within properties
- **Tenants**: Renters occupying units
- **Leases**: Rental agreements between tenants and properties
- **Rent Payments**: Payment records and tracking
- **Maintenance Requests**: Work orders and repairs
- **Expenses**: Property-related costs

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Flutter App                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │
│  │   Domain    │    │    Data     │    │       Presentation      │ │
│  │  Entities   │◄───│   Models    │◄───│    Providers/Blocs      │ │
│  └─────────────┘    └──────┬──────┘    └─────────────────────────┘ │
│                            │                                        │
│                     ┌──────┴──────┐                                 │
│                     │ Repository  │                                 │
│                     └──────┬──────┘                                 │
│            ┌───────────────┼───────────────┐                        │
│            ▼               ▼               ▼                        │
│    ┌───────────────┐ ┌───────────┐ ┌───────────────┐               │
│    │ Remote Source │ │ SQLite DB │ │ Shared Prefs  │               │
│    │   (API)       │ │ (Offline) │ │ (Auth Tokens) │               │
│    └───────────────┘ └───────────┘ └───────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │     SomniProperty Backend   │
              │     (PostgreSQL Database)   │
              └─────────────────────────────┘
```

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│      USER       │       │    PROPERTY     │       │      UNIT       │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ email           │       │ name            │       │ property_id (FK)│──┐
│ name            │       │ address         │       │ unit_number     │  │
│ role            │       │ city            │       │ bedrooms        │  │
│ phone           │       │ state           │       │ bathrooms       │  │
│ avatar_url      │       │ zip_code        │       │ sq_feet         │  │
│ groups[]        │       │ type            │       │ rent_amount     │  │
│ last_login      │       │ status          │       │ status          │  │
│ is_active       │       │ total_units     │       │ floor           │  │
│ created_at      │       │ occupied_units  │       │ description     │  │
│ updated_at      │       │ monthly_revenue │       │ amenities[]     │  │
└────────┬────────┘       │ description     │       │ created_at      │  │
         │                │ image_url       │       │ updated_at      │  │
         │                │ owner_id (FK)───┼───────┴─────────────────┘  │
         │                │ manager_id (FK) │                            │
         │                │ created_at      │◄───────────────────────────┘
         │                │ updated_at      │
         │                └────────┬────────┘
         │                         │
         │                         │ 1:N
         │                         ▼
         │                ┌─────────────────┐       ┌─────────────────┐
         │                │     TENANT      │       │      LEASE      │
         │                ├─────────────────┤       ├─────────────────┤
         │                │ id (PK)         │       │ id (PK)         │
         │                │ user_id (FK)────┼───────│ tenant_id (FK)  │
         │                │ first_name      │   ┌───│ unit_id (FK)    │
         │                │ last_name       │   │   │ property_id (FK)│
         │                │ email           │   │   │ start_date      │
         │                │ phone           │   │   │ end_date        │
         │                │ emergency_contact│  │   │ rent_amount     │
         │                │ move_in_date    │   │   │ deposit_amount  │
         │                │ move_out_date   │   │   │ payment_day     │
         │                │ notes           │   │   │ status          │
         │                │ status          │   │   │ terms           │
         │                │ created_at      │   │   │ document_url    │
         │                │ updated_at      │   │   │ created_at      │
         │                └─────────────────┘   │   │ updated_at      │
         │                                      │   └────────┬────────┘
         │                                      │            │
         │                                      │            │ 1:N
         │                                      │            ▼
         │                                      │   ┌─────────────────┐
         │                                      │   │  RENT_PAYMENT   │
         │                                      │   ├─────────────────┤
         │                                      │   │ id (PK)         │
         │                                      │   │ lease_id (FK)   │
         │                                      │   │ amount          │
         │                                      │   │ payment_date    │
         │                                      │   │ due_date        │
         │                                      │   │ payment_method  │
         │                                      │   │ status          │
         │                                      │   │ late_fee        │
         │                                      │   │ notes           │
         │                                      │   │ receipt_url     │
         │                                      │   │ created_at      │
         │                                      │   │ updated_at      │
         │                                      │   └─────────────────┘
         │                                      │
         │                                      ▼
┌────────┴────────┐                    ┌─────────────────┐
│   MAINTENANCE   │                    │     EXPENSE     │
├─────────────────┤                    ├─────────────────┤
│ id (PK)         │                    │ id (PK)         │
│ property_id (FK)│                    │ property_id (FK)│
│ unit_id (FK)    │                    │ description     │
│ tenant_id (FK)  │                    │ amount          │
│ title           │                    │ category        │
│ description     │                    │ date            │
│ category        │                    │ vendor          │
│ priority        │                    │ vendor_id (FK)  │
│ status          │                    │ receipt_url     │
│ assigned_to     │                    │ is_recurring    │
│ scheduled_date  │                    │ notes           │
│ completed_date  │                    │ created_at      │
│ cost            │                    │ updated_at      │
│ photos[]        │                    └─────────────────┘
│ notes           │
│ created_at      │
│ updated_at      │
└─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│     VENDOR      │       │    DOCUMENT     │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ name            │       │ entity_type     │
│ contact_name    │       │ entity_id       │
│ email           │       │ type            │
│ phone           │       │ name            │
│ address         │       │ url             │
│ specialty       │       │ size            │
│ hourly_rate     │       │ mime_type       │
│ notes           │       │ uploaded_by     │
│ is_active       │       │ created_at      │
│ created_at      │       │ updated_at      │
│ updated_at      │       └─────────────────┘
└─────────────────┘
```

---

## Core Entities

### 1. User (Authentication)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User email |
| name | VARCHAR(255) | NOT NULL | Display name |
| role | ENUM | NOT NULL | admin, manager, tenant, viewer |
| phone | VARCHAR(20) | NULL | Phone number |
| avatar_url | VARCHAR(500) | NULL | Profile image URL |
| groups | JSONB | DEFAULT '[]' | LDAP/OIDC groups |
| last_login | TIMESTAMP | NULL | Last login time |
| is_active | BOOLEAN | DEFAULT TRUE | Account status |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

### 2. Property

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| name | VARCHAR(255) | NOT NULL | Property name |
| address | VARCHAR(500) | NOT NULL | Street address |
| city | VARCHAR(100) | NOT NULL | City |
| state | VARCHAR(50) | NOT NULL | State/Province |
| zip_code | VARCHAR(20) | NOT NULL | Postal code |
| type | ENUM | NOT NULL | singleFamily, multiFamily, apartment, condo, townhouse, commercial, industrial, mixed |
| status | ENUM | NOT NULL | active, inactive, maintenance, listed, pending |
| total_units | INT | DEFAULT 1 | Total rental units |
| occupied_units | INT | DEFAULT 0 | Currently occupied |
| monthly_revenue | DECIMAL(12,2) | NULL | Monthly income |
| description | TEXT | NULL | Property description |
| image_url | VARCHAR(500) | NULL | Main image URL |
| owner_id | UUID | FK -> User | Property owner |
| manager_id | UUID | FK -> User, NULL | Property manager |
| latitude | DECIMAL(10,8) | NULL | GPS latitude |
| longitude | DECIMAL(11,8) | NULL | GPS longitude |
| year_built | INT | NULL | Construction year |
| sq_feet | INT | NULL | Total square footage |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

### 3. Unit

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| property_id | UUID | FK -> Property | Parent property |
| unit_number | VARCHAR(20) | NOT NULL | Unit identifier |
| bedrooms | INT | DEFAULT 1 | Number of bedrooms |
| bathrooms | DECIMAL(3,1) | DEFAULT 1 | Number of bathrooms |
| sq_feet | INT | NULL | Square footage |
| rent_amount | DECIMAL(10,2) | NOT NULL | Monthly rent |
| deposit_amount | DECIMAL(10,2) | NULL | Security deposit |
| status | ENUM | NOT NULL | available, occupied, maintenance, reserved |
| floor | INT | NULL | Floor number |
| description | TEXT | NULL | Unit description |
| amenities | JSONB | DEFAULT '[]' | List of amenities |
| images | JSONB | DEFAULT '[]' | Image URLs |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

### 4. Tenant

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK -> User, NULL | Linked user account |
| first_name | VARCHAR(100) | NOT NULL | First name |
| last_name | VARCHAR(100) | NOT NULL | Last name |
| email | VARCHAR(255) | NULL | Email address |
| phone | VARCHAR(20) | NULL | Phone number |
| emergency_name | VARCHAR(200) | NULL | Emergency contact name |
| emergency_phone | VARCHAR(20) | NULL | Emergency phone |
| move_in_date | DATE | NULL | Move-in date |
| move_out_date | DATE | NULL | Move-out date |
| notes | TEXT | NULL | Internal notes |
| status | ENUM | NOT NULL | active, inactive, pending, evicted |
| documents | JSONB | DEFAULT '[]' | Document references |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

### 5. Lease

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| tenant_id | UUID | FK -> Tenant | Tenant reference |
| unit_id | UUID | FK -> Unit | Unit reference |
| property_id | UUID | FK -> Property | Property reference |
| start_date | DATE | NOT NULL | Lease start date |
| end_date | DATE | NOT NULL | Lease end date |
| rent_amount | DECIMAL(10,2) | NOT NULL | Monthly rent |
| deposit_amount | DECIMAL(10,2) | NULL | Security deposit |
| deposit_status | ENUM | NULL | held, returned, partial, forfeited |
| payment_day | INT | DEFAULT 1 | Day of month rent due |
| late_fee | DECIMAL(10,2) | NULL | Late payment fee |
| grace_period_days | INT | DEFAULT 5 | Grace period |
| status | ENUM | NOT NULL | draft, pending, active, expired, terminated |
| terms | TEXT | NULL | Lease terms |
| document_url | VARCHAR(500) | NULL | Signed lease PDF |
| auto_renew | BOOLEAN | DEFAULT FALSE | Auto-renewal |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

### 6. RentPayment

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| lease_id | UUID | FK -> Lease | Lease reference |
| amount | DECIMAL(10,2) | NOT NULL | Payment amount |
| payment_date | DATE | NOT NULL | Date paid |
| due_date | DATE | NOT NULL | Original due date |
| payment_method | ENUM | NULL | cash, check, bank_transfer, credit_card, online |
| status | ENUM | NOT NULL | pending, completed, failed, refunded |
| late_fee | DECIMAL(10,2) | DEFAULT 0 | Late fee charged |
| reference_number | VARCHAR(100) | NULL | Transaction reference |
| notes | TEXT | NULL | Payment notes |
| receipt_url | VARCHAR(500) | NULL | Receipt document |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

### 7. MaintenanceRequest

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| property_id | UUID | FK -> Property | Property reference |
| unit_id | UUID | FK -> Unit, NULL | Unit reference |
| tenant_id | UUID | FK -> Tenant, NULL | Reporting tenant |
| title | VARCHAR(255) | NOT NULL | Request title |
| description | TEXT | NOT NULL | Detailed description |
| category | ENUM | NOT NULL | plumbing, electrical, hvac, appliance, structural, landscaping, pest, other |
| priority | ENUM | NOT NULL | low, normal, high, emergency |
| status | ENUM | NOT NULL | open, assigned, in_progress, completed, cancelled |
| assigned_to | UUID | FK -> User, NULL | Assigned worker |
| vendor_id | UUID | FK -> Vendor, NULL | External vendor |
| scheduled_date | DATETIME | NULL | Scheduled work date |
| completed_date | DATETIME | NULL | Completion date |
| estimated_cost | DECIMAL(10,2) | NULL | Estimated cost |
| actual_cost | DECIMAL(10,2) | NULL | Actual cost |
| photos | JSONB | DEFAULT '[]' | Photo URLs |
| notes | TEXT | NULL | Work notes |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

### 8. Expense

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| property_id | UUID | FK -> Property | Property reference |
| maintenance_id | UUID | FK -> Maintenance, NULL | Related maintenance |
| description | VARCHAR(500) | NOT NULL | Expense description |
| amount | DECIMAL(10,2) | NOT NULL | Expense amount |
| category | ENUM | NOT NULL | maintenance, utilities, insurance, taxes, management, supplies, legal, other |
| date | DATE | NOT NULL | Expense date |
| vendor | VARCHAR(255) | NULL | Vendor name |
| vendor_id | UUID | FK -> Vendor, NULL | Vendor reference |
| receipt_url | VARCHAR(500) | NULL | Receipt document |
| is_recurring | BOOLEAN | DEFAULT FALSE | Recurring expense |
| recurrence_period | ENUM | NULL | monthly, quarterly, yearly |
| tax_deductible | BOOLEAN | DEFAULT TRUE | Tax deductible |
| notes | TEXT | NULL | Additional notes |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

### 9. Vendor

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| name | VARCHAR(255) | NOT NULL | Company name |
| contact_name | VARCHAR(200) | NULL | Contact person |
| email | VARCHAR(255) | NULL | Email address |
| phone | VARCHAR(20) | NULL | Phone number |
| address | VARCHAR(500) | NULL | Business address |
| specialty | ENUM | NULL | plumbing, electrical, hvac, general, landscaping, cleaning, other |
| hourly_rate | DECIMAL(10,2) | NULL | Hourly rate |
| license_number | VARCHAR(100) | NULL | License/certification |
| insurance_info | TEXT | NULL | Insurance details |
| notes | TEXT | NULL | Internal notes |
| rating | DECIMAL(2,1) | NULL | Rating (1-5) |
| is_active | BOOLEAN | DEFAULT TRUE | Active status |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update |

---

## Flutter Data Models

### Domain Entities (`lib/features/*/domain/entities/`)

```dart
// property.dart - Already exists
class Property extends Equatable {
  final String id;
  final String name;
  final String address;
  final String city;
  final String state;
  final String zipCode;
  final PropertyType type;
  final PropertyStatus status;
  final int totalUnits;
  final int occupiedUnits;
  final double? monthlyRevenue;
  final String? description;
  final String? imageUrl;
  final String ownerId;
  final String? managerId;
  final DateTime createdAt;
  final DateTime updatedAt;
}

// unit.dart - NEW
class Unit extends Equatable {
  final String id;
  final String propertyId;
  final String unitNumber;
  final int bedrooms;
  final double bathrooms;
  final int? sqFeet;
  final double rentAmount;
  final double? depositAmount;
  final UnitStatus status;
  final int? floor;
  final String? description;
  final List<String> amenities;
  final List<String> images;
  final DateTime createdAt;
  final DateTime updatedAt;
}

// tenant.dart - NEW
class Tenant extends Equatable {
  final String id;
  final String? userId;
  final String firstName;
  final String lastName;
  final String? email;
  final String? phone;
  final String? emergencyName;
  final String? emergencyPhone;
  final DateTime? moveInDate;
  final DateTime? moveOutDate;
  final String? notes;
  final TenantStatus status;
  final DateTime createdAt;
  final DateTime updatedAt;

  String get fullName => '$firstName $lastName';
}

// lease.dart - NEW
class Lease extends Equatable {
  final String id;
  final String tenantId;
  final String unitId;
  final String propertyId;
  final DateTime startDate;
  final DateTime endDate;
  final double rentAmount;
  final double? depositAmount;
  final DepositStatus? depositStatus;
  final int paymentDay;
  final double? lateFee;
  final int gracePeriodDays;
  final LeaseStatus status;
  final String? terms;
  final String? documentUrl;
  final bool autoRenew;
  final DateTime createdAt;
  final DateTime updatedAt;

  bool get isActive => status == LeaseStatus.active;
  bool get isExpiringSoon => endDate.difference(DateTime.now()).inDays <= 60;
  int get daysRemaining => endDate.difference(DateTime.now()).inDays;
}

// rent_payment.dart - NEW
class RentPayment extends Equatable {
  final String id;
  final String leaseId;
  final double amount;
  final DateTime paymentDate;
  final DateTime dueDate;
  final PaymentMethod? paymentMethod;
  final PaymentStatus status;
  final double lateFee;
  final String? referenceNumber;
  final String? notes;
  final String? receiptUrl;
  final DateTime createdAt;
  final DateTime updatedAt;

  bool get isLate => paymentDate.isAfter(dueDate);
  bool get isOverdue => status == PaymentStatus.pending &&
                        DateTime.now().isAfter(dueDate);
}

// maintenance_request.dart - NEW
class MaintenanceRequest extends Equatable {
  final String id;
  final String propertyId;
  final String? unitId;
  final String? tenantId;
  final String title;
  final String description;
  final MaintenanceCategory category;
  final Priority priority;
  final MaintenanceStatus status;
  final String? assignedTo;
  final String? vendorId;
  final DateTime? scheduledDate;
  final DateTime? completedDate;
  final double? estimatedCost;
  final double? actualCost;
  final List<String> photos;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;
}

// expense.dart - NEW
class Expense extends Equatable {
  final String id;
  final String propertyId;
  final String? maintenanceId;
  final String description;
  final double amount;
  final ExpenseCategory category;
  final DateTime date;
  final String? vendor;
  final String? vendorId;
  final String? receiptUrl;
  final bool isRecurring;
  final RecurrencePeriod? recurrencePeriod;
  final bool taxDeductible;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;
}

// vendor.dart - NEW
class Vendor extends Equatable {
  final String id;
  final String name;
  final String? contactName;
  final String? email;
  final String? phone;
  final String? address;
  final VendorSpecialty? specialty;
  final double? hourlyRate;
  final String? licenseNumber;
  final String? insuranceInfo;
  final String? notes;
  final double? rating;
  final bool isActive;
  final DateTime createdAt;
  final DateTime updatedAt;
}
```

### Enumerations

```dart
// enums.dart
enum PropertyType {
  singleFamily('Single Family'),
  multiFamily('Multi-Family'),
  apartment('Apartment'),
  condo('Condo'),
  townhouse('Townhouse'),
  commercial('Commercial'),
  industrial('Industrial'),
  mixed('Mixed Use');

  final String displayName;
  const PropertyType(this.displayName);
}

enum PropertyStatus {
  active('Active'),
  inactive('Inactive'),
  maintenance('Under Maintenance'),
  listed('Listed for Sale'),
  pending('Pending');

  final String displayName;
  const PropertyStatus(this.displayName);
}

enum UnitStatus {
  available('Available'),
  occupied('Occupied'),
  maintenance('Maintenance'),
  reserved('Reserved');

  final String displayName;
  const UnitStatus(this.displayName);
}

enum TenantStatus {
  active('Active'),
  inactive('Inactive'),
  pending('Pending'),
  evicted('Evicted');

  final String displayName;
  const TenantStatus(this.displayName);
}

enum LeaseStatus {
  draft('Draft'),
  pending('Pending Signature'),
  active('Active'),
  expired('Expired'),
  terminated('Terminated');

  final String displayName;
  const LeaseStatus(this.displayName);
}

enum DepositStatus {
  held('Held'),
  returned('Returned'),
  partial('Partially Returned'),
  forfeited('Forfeited');

  final String displayName;
  const DepositStatus(this.displayName);
}

enum PaymentMethod {
  cash('Cash'),
  check('Check'),
  bankTransfer('Bank Transfer'),
  creditCard('Credit Card'),
  online('Online Payment');

  final String displayName;
  const PaymentMethod(this.displayName);
}

enum PaymentStatus {
  pending('Pending'),
  completed('Completed'),
  failed('Failed'),
  refunded('Refunded');

  final String displayName;
  const PaymentStatus(this.displayName);
}

enum MaintenanceCategory {
  plumbing('Plumbing'),
  electrical('Electrical'),
  hvac('HVAC'),
  appliance('Appliance'),
  structural('Structural'),
  landscaping('Landscaping'),
  pest('Pest Control'),
  other('Other');

  final String displayName;
  const MaintenanceCategory(this.displayName);
}

enum Priority {
  low('Low'),
  normal('Normal'),
  high('High'),
  emergency('Emergency');

  final String displayName;
  const Priority(this.displayName);
}

enum MaintenanceStatus {
  open('Open'),
  assigned('Assigned'),
  inProgress('In Progress'),
  completed('Completed'),
  cancelled('Cancelled');

  final String displayName;
  const MaintenanceStatus(this.displayName);
}

enum ExpenseCategory {
  maintenance('Maintenance'),
  utilities('Utilities'),
  insurance('Insurance'),
  taxes('Property Taxes'),
  management('Management'),
  supplies('Supplies'),
  legal('Legal'),
  other('Other');

  final String displayName;
  const ExpenseCategory(this.displayName);
}

enum RecurrencePeriod {
  monthly('Monthly'),
  quarterly('Quarterly'),
  yearly('Yearly');

  final String displayName;
  const RecurrencePeriod(this.displayName);
}

enum VendorSpecialty {
  plumbing('Plumbing'),
  electrical('Electrical'),
  hvac('HVAC'),
  general('General Contractor'),
  landscaping('Landscaping'),
  cleaning('Cleaning'),
  other('Other');

  final String displayName;
  const VendorSpecialty(this.displayName);
}
```

---

## SQLite Local Schema

### Database Creation Script

```dart
// lib/core/database/database_helper.dart
class DatabaseHelper {
  static const String databaseName = 'somni_property.db';
  static const int databaseVersion = 1;

  static Future<Database> initDatabase() async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, databaseName);

    return openDatabase(
      path,
      version: databaseVersion,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
  }

  static Future<void> _onCreate(Database db, int version) async {
    // Sync metadata table
    await db.execute('''
      CREATE TABLE sync_metadata (
        table_name TEXT PRIMARY KEY,
        last_sync_at TEXT,
        sync_token TEXT,
        is_dirty INTEGER DEFAULT 0
      )
    ''');

    // Properties table
    await db.execute('''
      CREATE TABLE properties (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        zip_code TEXT NOT NULL,
        type TEXT NOT NULL,
        status TEXT NOT NULL,
        total_units INTEGER DEFAULT 1,
        occupied_units INTEGER DEFAULT 0,
        monthly_revenue REAL,
        description TEXT,
        image_url TEXT,
        owner_id TEXT NOT NULL,
        manager_id TEXT,
        latitude REAL,
        longitude REAL,
        year_built INTEGER,
        sq_feet INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_synced INTEGER DEFAULT 1,
        local_updated_at TEXT
      )
    ''');
    await db.execute('CREATE INDEX idx_properties_owner ON properties(owner_id)');
    await db.execute('CREATE INDEX idx_properties_status ON properties(status)');

    // Units table
    await db.execute('''
      CREATE TABLE units (
        id TEXT PRIMARY KEY,
        property_id TEXT NOT NULL,
        unit_number TEXT NOT NULL,
        bedrooms INTEGER DEFAULT 1,
        bathrooms REAL DEFAULT 1.0,
        sq_feet INTEGER,
        rent_amount REAL NOT NULL,
        deposit_amount REAL,
        status TEXT NOT NULL,
        floor INTEGER,
        description TEXT,
        amenities TEXT DEFAULT '[]',
        images TEXT DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_synced INTEGER DEFAULT 1,
        local_updated_at TEXT,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
      )
    ''');
    await db.execute('CREATE INDEX idx_units_property ON units(property_id)');
    await db.execute('CREATE INDEX idx_units_status ON units(status)');

    // Tenants table
    await db.execute('''
      CREATE TABLE tenants (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        emergency_name TEXT,
        emergency_phone TEXT,
        move_in_date TEXT,
        move_out_date TEXT,
        notes TEXT,
        status TEXT NOT NULL,
        documents TEXT DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_synced INTEGER DEFAULT 1,
        local_updated_at TEXT
      )
    ''');
    await db.execute('CREATE INDEX idx_tenants_status ON tenants(status)');
    await db.execute('CREATE INDEX idx_tenants_email ON tenants(email)');

    // Leases table
    await db.execute('''
      CREATE TABLE leases (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        unit_id TEXT NOT NULL,
        property_id TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        rent_amount REAL NOT NULL,
        deposit_amount REAL,
        deposit_status TEXT,
        payment_day INTEGER DEFAULT 1,
        late_fee REAL,
        grace_period_days INTEGER DEFAULT 5,
        status TEXT NOT NULL,
        terms TEXT,
        document_url TEXT,
        auto_renew INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_synced INTEGER DEFAULT 1,
        local_updated_at TEXT,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id),
        FOREIGN KEY (unit_id) REFERENCES units(id),
        FOREIGN KEY (property_id) REFERENCES properties(id)
      )
    ''');
    await db.execute('CREATE INDEX idx_leases_tenant ON leases(tenant_id)');
    await db.execute('CREATE INDEX idx_leases_property ON leases(property_id)');
    await db.execute('CREATE INDEX idx_leases_status ON leases(status)');
    await db.execute('CREATE INDEX idx_leases_end_date ON leases(end_date)');

    // Rent Payments table
    await db.execute('''
      CREATE TABLE rent_payments (
        id TEXT PRIMARY KEY,
        lease_id TEXT NOT NULL,
        amount REAL NOT NULL,
        payment_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        payment_method TEXT,
        status TEXT NOT NULL,
        late_fee REAL DEFAULT 0,
        reference_number TEXT,
        notes TEXT,
        receipt_url TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_synced INTEGER DEFAULT 1,
        local_updated_at TEXT,
        FOREIGN KEY (lease_id) REFERENCES leases(id) ON DELETE CASCADE
      )
    ''');
    await db.execute('CREATE INDEX idx_payments_lease ON rent_payments(lease_id)');
    await db.execute('CREATE INDEX idx_payments_status ON rent_payments(status)');
    await db.execute('CREATE INDEX idx_payments_date ON rent_payments(payment_date)');

    // Maintenance Requests table
    await db.execute('''
      CREATE TABLE maintenance_requests (
        id TEXT PRIMARY KEY,
        property_id TEXT NOT NULL,
        unit_id TEXT,
        tenant_id TEXT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL,
        assigned_to TEXT,
        vendor_id TEXT,
        scheduled_date TEXT,
        completed_date TEXT,
        estimated_cost REAL,
        actual_cost REAL,
        photos TEXT DEFAULT '[]',
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_synced INTEGER DEFAULT 1,
        local_updated_at TEXT,
        FOREIGN KEY (property_id) REFERENCES properties(id),
        FOREIGN KEY (unit_id) REFERENCES units(id),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
      )
    ''');
    await db.execute('CREATE INDEX idx_maintenance_property ON maintenance_requests(property_id)');
    await db.execute('CREATE INDEX idx_maintenance_status ON maintenance_requests(status)');
    await db.execute('CREATE INDEX idx_maintenance_priority ON maintenance_requests(priority)');

    // Expenses table
    await db.execute('''
      CREATE TABLE expenses (
        id TEXT PRIMARY KEY,
        property_id TEXT NOT NULL,
        maintenance_id TEXT,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        date TEXT NOT NULL,
        vendor TEXT,
        vendor_id TEXT,
        receipt_url TEXT,
        is_recurring INTEGER DEFAULT 0,
        recurrence_period TEXT,
        tax_deductible INTEGER DEFAULT 1,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_synced INTEGER DEFAULT 1,
        local_updated_at TEXT,
        FOREIGN KEY (property_id) REFERENCES properties(id)
      )
    ''');
    await db.execute('CREATE INDEX idx_expenses_property ON expenses(property_id)');
    await db.execute('CREATE INDEX idx_expenses_category ON expenses(category)');
    await db.execute('CREATE INDEX idx_expenses_date ON expenses(date)');

    // Vendors table
    await db.execute('''
      CREATE TABLE vendors (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        contact_name TEXT,
        email TEXT,
        phone TEXT,
        address TEXT,
        specialty TEXT,
        hourly_rate REAL,
        license_number TEXT,
        insurance_info TEXT,
        notes TEXT,
        rating REAL,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_synced INTEGER DEFAULT 1,
        local_updated_at TEXT
      )
    ''');
    await db.execute('CREATE INDEX idx_vendors_specialty ON vendors(specialty)');
    await db.execute('CREATE INDEX idx_vendors_active ON vendors(is_active)');

    // Pending operations queue (for offline sync)
    await db.execute('''
      CREATE TABLE pending_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        operation TEXT NOT NULL,
        record_id TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        last_error TEXT
      )
    ''');
  }

  static Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    // Handle migrations here
  }
}
```

---

## Sync Strategy

### Sync Architecture

```dart
// lib/core/sync/sync_service.dart
abstract class SyncService {
  /// Full sync - downloads all data from server
  Future<void> fullSync();

  /// Incremental sync - only changed data since last sync
  Future<void> incrementalSync();

  /// Push local changes to server
  Future<void> pushPendingChanges();

  /// Resolve conflicts between local and remote
  Future<void> resolveConflicts(List<ConflictRecord> conflicts);
}
```

### Sync Strategy by Entity

| Entity | Sync Strategy | Conflict Resolution |
|--------|---------------|---------------------|
| **Property** | Bidirectional | Server wins (admin-managed) |
| **Unit** | Bidirectional | Server wins |
| **Tenant** | Bidirectional | Server wins |
| **Lease** | Server → Client | Server authoritative |
| **RentPayment** | Bidirectional | Merge (additive) |
| **MaintenanceRequest** | Bidirectional | Last-write wins |
| **Expense** | Bidirectional | Merge (additive) |
| **Vendor** | Server → Client | Server authoritative |

### Offline-First Workflow

```dart
// lib/core/sync/sync_manager.dart
class SyncManager {
  final LocalDatabase _localDb;
  final RemoteApiClient _api;
  final ConnectivityService _connectivity;

  /// Create record locally, queue for sync
  Future<T> create<T>(T entity) async {
    // 1. Generate local UUID
    final localId = uuid.v4();

    // 2. Save to local database with is_synced = false
    await _localDb.insert(entity.copyWith(
      id: localId,
      isSynced: false,
      localUpdatedAt: DateTime.now(),
    ));

    // 3. Queue operation for sync
    await _localDb.queueOperation(
      table: entity.tableName,
      operation: 'CREATE',
      recordId: localId,
      data: entity.toJson(),
    );

    // 4. Try immediate sync if online
    if (await _connectivity.isConnected) {
      await _syncEntity(entity);
    }

    return entity;
  }

  /// Sync pending operations when back online
  Future<void> syncPendingOperations() async {
    final pending = await _localDb.getPendingOperations();

    for (final op in pending) {
      try {
        switch (op.operation) {
          case 'CREATE':
            final remoteId = await _api.create(op.tableName, op.data);
            await _localDb.updateRemoteId(op.recordId, remoteId);
            break;
          case 'UPDATE':
            await _api.update(op.tableName, op.recordId, op.data);
            break;
          case 'DELETE':
            await _api.delete(op.tableName, op.recordId);
            break;
        }

        await _localDb.markAsSynced(op.recordId);
        await _localDb.deletePendingOperation(op.id);
      } catch (e) {
        await _localDb.incrementAttempts(op.id, e.toString());
      }
    }
  }
}
```

### Sync Token Implementation

```dart
// Incremental sync using timestamps
class IncrementalSyncService {
  Future<void> syncTable(String tableName) async {
    // Get last sync timestamp
    final lastSync = await _db.getLastSyncTime(tableName);

    // Fetch changes since last sync
    final changes = await _api.getChanges(
      table: tableName,
      since: lastSync,
    );

    // Apply changes to local database
    for (final change in changes) {
      switch (change.operation) {
        case 'INSERT':
        case 'UPDATE':
          await _db.upsert(tableName, change.data);
          break;
        case 'DELETE':
          await _db.delete(tableName, change.id);
          break;
      }
    }

    // Update sync metadata
    await _db.updateSyncTime(tableName, DateTime.now());
  }
}
```

---

## API Endpoints Reference

### Base URLs

```dart
// Production endpoints
const String tailscaleBaseUrl = 'https://property.tail58c8e4.ts.net';
const String localBaseUrl = 'https://property.home.lan';
const String publicBaseUrl = 'https://property.somni-labs.tech';
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| **Properties** | | |
| GET | `/api/v1/properties` | List all properties |
| GET | `/api/v1/properties/{id}` | Get property details |
| POST | `/api/v1/properties` | Create property |
| PUT | `/api/v1/properties/{id}` | Update property |
| DELETE | `/api/v1/properties/{id}` | Delete property |
| **Units** | | |
| GET | `/api/v1/properties/{id}/units` | List units in property |
| GET | `/api/v1/units/{id}` | Get unit details |
| POST | `/api/v1/units` | Create unit |
| PUT | `/api/v1/units/{id}` | Update unit |
| DELETE | `/api/v1/units/{id}` | Delete unit |
| **Tenants** | | |
| GET | `/api/v1/tenants` | List all tenants |
| GET | `/api/v1/tenants/{id}` | Get tenant details |
| POST | `/api/v1/tenants` | Create tenant |
| PUT | `/api/v1/tenants/{id}` | Update tenant |
| DELETE | `/api/v1/tenants/{id}` | Delete tenant |
| **Leases** | | |
| GET | `/api/v1/leases` | List all leases |
| GET | `/api/v1/leases/{id}` | Get lease details |
| GET | `/api/v1/leases/expiring` | Get expiring leases |
| POST | `/api/v1/leases` | Create lease |
| PUT | `/api/v1/leases/{id}` | Update lease |
| POST | `/api/v1/leases/{id}/renew` | Renew lease |
| POST | `/api/v1/leases/{id}/terminate` | Terminate lease |
| **Rent Payments** | | |
| GET | `/api/v1/rent-payments` | List payments |
| GET | `/api/v1/rent-payments/overdue` | Get overdue payments |
| POST | `/api/v1/rent-payments` | Record payment |
| PUT | `/api/v1/rent-payments/{id}` | Update payment |
| **Maintenance** | | |
| GET | `/api/v1/maintenance` | List requests |
| GET | `/api/v1/maintenance/{id}` | Get request details |
| POST | `/api/v1/maintenance` | Create request |
| PUT | `/api/v1/maintenance/{id}` | Update request |
| POST | `/api/v1/maintenance/{id}/assign` | Assign worker |
| POST | `/api/v1/maintenance/{id}/complete` | Mark complete |
| **Expenses** | | |
| GET | `/api/v1/expenses` | List expenses |
| GET | `/api/v1/properties/{id}/expenses` | Property expenses |
| POST | `/api/v1/expenses` | Record expense |
| PUT | `/api/v1/expenses/{id}` | Update expense |
| DELETE | `/api/v1/expenses/{id}` | Delete expense |
| **Vendors** | | |
| GET | `/api/v1/vendors` | List vendors |
| GET | `/api/v1/vendors/{id}` | Get vendor details |
| POST | `/api/v1/vendors` | Create vendor |
| PUT | `/api/v1/vendors/{id}` | Update vendor |
| **Sync** | | |
| GET | `/api/v1/sync/changes` | Get changes since timestamp |
| POST | `/api/v1/sync/batch` | Batch sync operations |

---

## Implementation Checklist

### Phase 1: Core Data Layer
- [ ] Create all domain entities in `lib/features/*/domain/entities/`
- [ ] Create all data models in `lib/features/*/data/models/`
- [ ] Implement DatabaseHelper with SQLite schema
- [ ] Create repository interfaces
- [ ] Implement local data sources

### Phase 2: Remote Integration
- [ ] Implement API client for each endpoint
- [ ] Create remote data sources
- [ ] Implement repository implementations with offline-first pattern

### Phase 3: Sync Implementation
- [ ] Implement SyncManager
- [ ] Create pending operations queue
- [ ] Implement conflict resolution
- [ ] Add background sync worker

### Phase 4: Testing
- [ ] Unit tests for models
- [ ] Unit tests for repositories
- [ ] Integration tests for sync
- [ ] End-to-end data flow tests

---

**Document Version**: 1.0.0
**Created**: 2025-12-04
**Author**: Claude Code Assistant
