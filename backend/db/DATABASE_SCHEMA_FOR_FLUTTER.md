# Somni Property Manager – Database Schema for Flutter

**Updated:** 2025-12-05  
**Source status:** The repository does not contain `apps/somni-property-manager/backend/db` migrations or schema files. The schema below is **inferred** from the SomniProperty API clients (`apps/somnisync/src/connectors/property.py`, Home Assistant connectors) and product requirements. Treat this as the baseline contract for implementing the actual backend migrations and Flutter data layer.

---

## What Was Found (Evidence)

- No backend code or migrations exist in `apps/somni-property-manager/backend/db` (directory was empty and created for this doc).
- API surface inferred from integration clients:
  - Property CRUD: `/api/properties`
  - Tenants: `/api/tenants`
  - Leases & expiring leases: `/api/leases`, `/api/leases/expiring`
  - Rent payments: `/api/rent-payments`, `/api/rent-payments/overdue`
  - Maintenance: `/api/maintenance`
  - Expenses: `/api/expenses`
  - HA edge sync: `/api/v1/sync/devices`, `/api/v1/sync/health`, `/api/v1/commands`
- Deployment manifest expects PostgreSQL (`somni_property_manager`) with Alembic migrations run by the backend container.

---

## Relational Schema (PostgreSQL)

### Core tables

- **properties**
  - `id` UUID PK
  - `name` text not null
  - `type` text (residential, commercial, mixed, hoa)
  - `address_line1` text, `address_line2` text, `city` text, `state` text, `postal_code` text, `country` text
  - `timezone` text default `UTC`
  - `status` text (active, archived)
  - `created_at` timestamptz default now(), `updated_at` timestamptz default now()
  - Indexes: `(status)`, `(city, state)`, btree on `(lower(name))`

- **units**
  - `id` UUID PK
  - `property_id` UUID FK → properties(id) on delete cascade
  - `unit_number` text not null
  - `floor` int, `bedrooms` int, `bathrooms` numeric(3,1), `square_feet` int
  - `rent_target` numeric(12,2), `is_vacant` bool default true
  - `created_at`, `updated_at`
  - Constraints: unique(property_id, unit_number)
  - Indexes: `(property_id)`, `(is_vacant)`

- **tenants**
  - `id` UUID PK
  - `property_id` UUID FK → properties(id) on delete set null
  - `unit_id` UUID FK → units(id) on delete set null
  - `first_name` text not null, `last_name` text not null
  - `email` text, `phone` text
  - `move_in_date` date, `move_out_date` date
  - `status` text default `prospect` (prospect, active, past_due, moved_out)
  - `created_at`, `updated_at`
  - Indexes: `(property_id)`, `(unit_id)`, `lower(email)`

- **leases**
  - `id` UUID PK
  - `property_id` UUID FK → properties(id) on delete cascade
  - `unit_id` UUID FK → units(id) on delete cascade
  - `primary_tenant_id` UUID FK → tenants(id) on delete set null
  - `start_date` date not null, `end_date` date not null
  - `rent_amount` numeric(12,2) not null
  - `deposit_amount` numeric(12,2) default 0
  - `billing_day` smallint default 1  -- day of month rent is due
  - `status` text default `draft` (draft, active, renewal_pending, terminated)
  - `auto_pay` bool default false, `late_fee_percent` numeric(5,2) default 0
  - `created_at`, `updated_at`
  - Indexes: `(property_id, unit_id)`, `(status)`, `(end_date)`

- **lease_tenants** (many-to-many for roommates)
  - `lease_id` UUID FK → leases(id) on delete cascade
  - `tenant_id` UUID FK → tenants(id) on delete cascade
  - `role` text default `tenant` (tenant, guarantor, cosigner)
  - PK: (lease_id, tenant_id)

- **rent_payments**
  - `id` UUID PK
  - `lease_id` UUID FK → leases(id) on delete cascade
  - `tenant_id` UUID FK → tenants(id) on delete set null
  - `due_date` date not null
  - `amount_due` numeric(12,2) not null
  - `amount_paid` numeric(12,2) default 0
  - `payment_date` date, `payment_method` text (cash, check, ach, card)
  - `status` text default `pending` (pending, paid, partial, overdue, waived)
  - `reference` text, `notes` text
  - `created_at`, `updated_at`
  - Indexes: `(lease_id, due_date)`, `(status)`, `(tenant_id)`

- **maintenance_requests**
  - `id` UUID PK
  - `property_id` UUID FK → properties(id) on delete cascade
  - `unit_id` UUID FK → units(id) on delete set null
  - `tenant_id` UUID FK → tenants(id) on delete set null
  - `title` text not null, `description` text
  - `priority` text default `medium` (low, medium, high, urgent)
  - `category` text (plumbing, electrical, hvac, security, general)
  - `status` text default `open` (open, in_progress, scheduled, completed, cancelled)
  - `opened_at` timestamptz default now(), `due_at` timestamptz, `closed_at` timestamptz
  - `cost_estimate` numeric(12,2), `cost_actual` numeric(12,2)
  - `vendor_id` UUID FK → vendors(id) on delete set null
  - Indexes: `(property_id)`, `(status, priority)`, `(tenant_id)`

- **vendors**
  - `id` UUID PK
  - `name` text not null
  - `contact_email` text, `contact_phone` text
  - `service_categories` text[] (optional)
  - `created_at`, `updated_at`

- **property_expenses**
  - `id` UUID PK
  - `property_id` UUID FK → properties(id) on delete cascade
  - `unit_id` UUID FK → units(id) on delete set null
  - `vendor_id` UUID FK → vendors(id) on delete set null
  - `description` text not null
  - `category` text (taxes, utilities, maintenance, capex, insurance, hoa, other)
  - `amount` numeric(12,2) not null
  - `expense_date` date not null
  - `invoice_url` text, `receipt_url` text
  - `status` text default `recorded` (recorded, reimbursed, disputed)
  - `created_at`, `updated_at`
  - Indexes: `(property_id, expense_date)`, `(category)`, `(vendor_id)`

- **documents**
  - `id` UUID PK
  - `property_id` UUID FK → properties(id) on delete cascade
  - `unit_id` UUID FK → units(id) on delete set null
  - `tenant_id` UUID FK → tenants(id) on delete set null
  - `lease_id` UUID FK → leases(id) on delete set null
  - `title` text not null, `doc_type` text (lease, inspection, photo, receipt, id)
  - `file_url` text not null
  - `uploaded_at` timestamptz default now()
  - Indexes: `(lease_id)`, `(tenant_id)`

### Home Assistant / Edge sync tables

- **hubs**
  - `id` UUID PK  -- Hub ID from HA connector
  - `name` text, `location` text, `property_id` UUID FK → properties(id) on delete set null
  - `last_seen_at` timestamptz, `status` text default `online`
  - Indexes: `(property_id)`, `(status)`

- **devices**
  - `id` UUID PK
  - `hub_id` UUID FK → hubs(id) on delete cascade
  - `entity_id` text not null
  - `domain` text (light, sensor, lock, climate, etc.)
  - `name` text, `area` text
  - `state` text, `attributes` jsonb default '{}'::jsonb
  - `last_reported_at` timestamptz
  - Constraints: unique(hub_id, entity_id)
  - Indexes: `(hub_id)`, `gin(attributes)`

- **device_syncs**
  - `id` UUID PK
  - `hub_id` UUID FK → hubs(id) on delete cascade
  - `sync_id` text not null
  - `added` int, `updated` int, `removed` int
  - `created_at` timestamptz default now()
  - Indexes: `(hub_id, created_at desc)`

- **commands**
  - `id` UUID PK
  - `hub_id` UUID FK → hubs(id) on delete cascade
  - `target_entity` text not null
  - `action` text not null
  - `payload` jsonb default '{}'::jsonb
  - `status` text default `pending` (pending, sent, success, failed)
  - `issued_at` timestamptz default now(), `executed_at` timestamptz
  - `result` jsonb
  - Indexes: `(hub_id, status)`, `(issued_at desc)`

- **health_reports**
  - `id` UUID PK
  - `hub_id` UUID FK → hubs(id) on delete cascade
  - `cpu_usage` numeric(5,2), `memory_usage` numeric(5,2), `disk_usage` numeric(5,2), `temperature` numeric(5,2)
  - `services` jsonb default '{}'::jsonb
  - `reported_at` timestamptz default now()
  - Indexes: `(hub_id, reported_at desc)`

### Relationships at a glance

- properties 1→N units, tenants, leases, maintenance_requests, expenses, documents, hubs
- units 1→N leases, maintenance_requests; optional link in tenants/expenses/documents
- leases N↔N tenants via lease_tenants; leases 1→N rent_payments, documents
- hubs 1→N devices, device_syncs, commands, health_reports

---

## Migration Plan (not present yet)

1) **0001_initial.py**  
   - Create core tables: properties, units, tenants, leases, lease_tenants, rent_payments, maintenance_requests, vendors, property_expenses, documents.  
   - Add timestamp triggers/defaults and indexes listed above.

2) **0002_home_assistant_sync.py**  
   - Add hubs, devices, device_syncs, commands, health_reports.  
   - Seed command statuses (`pending`, `sent`, `success`, `failed`) and maintenance priorities if needed.

3) **0003_financial_enhancements.py** (optional)  
   - Add late fee defaults, autopay flags, `amount_paid` tracking and overdue views/materialized views for dashboard KPIs.

Each migration should be Alembic-based with `revision`/`down_revision` identifiers and compatibility with PostgreSQL 15.

---

## Flutter Data Models (Dart)

The models below mirror the inferred schema and can back both REST DTOs and offline SQLite entities. Use `json_serializable` or `freezed` for immutability; shown as plain classes for clarity.

```dart
class Property {
  final String id;
  final String name;
  final String? type;
  final String? addressLine1;
  final String? addressLine2;
  final String? city;
  final String? state;
  final String? postalCode;
  final String? country;
  final String? timezone;
  final String status;

  Property({
    required this.id,
    required this.name,
    this.type,
    this.addressLine1,
    this.addressLine2,
    this.city,
    this.state,
    this.postalCode,
    this.country,
    this.timezone = 'UTC',
    this.status = 'active',
  });

  factory Property.fromJson(Map<String, dynamic> json) => Property(
        id: json['id'],
        name: json['name'],
        type: json['type'],
        addressLine1: json['address_line1'],
        addressLine2: json['address_line2'],
        city: json['city'],
        state: json['state'],
        postalCode: json['postal_code'],
        country: json['country'],
        timezone: json['timezone'] ?? 'UTC',
        status: json['status'] ?? 'active',
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'type': type,
        'address_line1': addressLine1,
        'address_line2': addressLine2,
        'city': city,
        'state': state,
        'postal_code': postalCode,
        'country': country,
        'timezone': timezone,
        'status': status,
      };
}
```

```dart
class Unit {
  final String id;
  final String propertyId;
  final String unitNumber;
  final int? floor;
  final int? bedrooms;
  final double? bathrooms;
  final int? squareFeet;
  final double? rentTarget;
  final bool isVacant;

  Unit({
    required this.id,
    required this.propertyId,
    required this.unitNumber,
    this.floor,
    this.bedrooms,
    this.bathrooms,
    this.squareFeet,
    this.rentTarget,
    this.isVacant = true,
  });
}
```

```dart
class Tenant {
  final String id;
  final String? propertyId;
  final String? unitId;
  final String firstName;
  final String lastName;
  final String? email;
  final String? phone;
  final DateTime? moveInDate;
  final DateTime? moveOutDate;
  final String status;

  Tenant({
    required this.id,
    this.propertyId,
    this.unitId,
    required this.firstName,
    required this.lastName,
    this.email,
    this.phone,
    this.moveInDate,
    this.moveOutDate,
    this.status = 'prospect',
  });
}
```

```dart
class Lease {
  final String id;
  final String propertyId;
  final String unitId;
  final String? primaryTenantId;
  final DateTime startDate;
  final DateTime endDate;
  final double rentAmount;
  final double depositAmount;
  final int billingDay;
  final String status;
  final bool autoPay;
  final double lateFeePercent;

  Lease({
    required this.id,
    required this.propertyId,
    required this.unitId,
    this.primaryTenantId,
    required this.startDate,
    required this.endDate,
    required this.rentAmount,
    this.depositAmount = 0,
    this.billingDay = 1,
    this.status = 'draft',
    this.autoPay = false,
    this.lateFeePercent = 0,
  });
}
```

```dart
class RentPayment {
  final String id;
  final String leaseId;
  final String? tenantId;
  final DateTime dueDate;
  final double amountDue;
  final double amountPaid;
  final DateTime? paymentDate;
  final String status;
  final String? paymentMethod;
  final String? reference;

  RentPayment({
    required this.id,
    required this.leaseId,
    this.tenantId,
    required this.dueDate,
    required this.amountDue,
    this.amountPaid = 0,
    this.paymentDate,
    this.status = 'pending',
    this.paymentMethod,
    this.reference,
  });
}
```

```dart
class MaintenanceRequest {
  final String id;
  final String propertyId;
  final String? unitId;
  final String? tenantId;
  final String title;
  final String? description;
  final String priority;
  final String status;
  final String? category;
  final DateTime openedAt;
  final DateTime? dueAt;
  final DateTime? closedAt;
  final double? costEstimate;
  final double? costActual;

  MaintenanceRequest({
    required this.id,
    required this.propertyId,
    this.unitId,
    this.tenantId,
    required this.title,
    this.description,
    this.priority = 'medium',
    this.status = 'open',
    this.category,
    DateTime? openedAt,
    this.dueAt,
    this.closedAt,
    this.costEstimate,
    this.costActual,
  }) : openedAt = openedAt ?? DateTime.now();
}
```

```dart
class Hub {
  final String id;
  final String? name;
  final String? location;
  final String? propertyId;
  final DateTime? lastSeenAt;
  final String status;

  Hub({
    required this.id,
    this.name,
    this.location,
    this.propertyId,
    this.lastSeenAt,
    this.status = 'online',
  });
}
```

```dart
class Device {
  final String id;
  final String hubId;
  final String entityId;
  final String? domain;
  final String? name;
  final String? area;
  final String? state;
  final Map<String, dynamic> attributes;
  final DateTime? lastReportedAt;

  Device({
    required this.id,
    required this.hubId,
    required this.entityId,
    this.domain,
    this.name,
    this.area,
    this.state,
    this.attributes = const {},
    this.lastReportedAt,
  });
}
```

Reuse the same DTOs for SQLite; primary keys remain `TEXT` storing UUID strings.

---

## SQLite Offline-First Schema (Flutter)

Use `sqflite`/`drift` with the same logical structure; keep columns camelCase in Dart but snake_case in SQLite for consistency with the API.

```sql
-- properties
CREATE TABLE properties (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT,
  address_line1 TEXT,
  address_line2 TEXT,
  city TEXT,
  state TEXT,
  postal_code TEXT,
  country TEXT,
  timezone TEXT DEFAULT 'UTC',
  status TEXT DEFAULT 'active',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_properties_status ON properties(status);

-- units
CREATE TABLE units (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL,
  unit_number TEXT NOT NULL,
  floor INTEGER,
  bedrooms INTEGER,
  bathrooms REAL,
  square_feet INTEGER,
  rent_target REAL,
  is_vacant INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(property_id) REFERENCES properties(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX idx_units_property_unit ON units(property_id, unit_number);

-- tenants
CREATE TABLE tenants (
  id TEXT PRIMARY KEY,
  property_id TEXT,
  unit_id TEXT,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  move_in_date TEXT,
  move_out_date TEXT,
  status TEXT DEFAULT 'prospect',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_tenants_property ON tenants(property_id);
CREATE INDEX idx_tenants_unit ON tenants(unit_id);

-- leases
CREATE TABLE leases (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL,
  unit_id TEXT NOT NULL,
  primary_tenant_id TEXT,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  rent_amount REAL NOT NULL,
  deposit_amount REAL DEFAULT 0,
  billing_day INTEGER DEFAULT 1,
  status TEXT DEFAULT 'draft',
  auto_pay INTEGER DEFAULT 0,
  late_fee_percent REAL DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_leases_property_unit ON leases(property_id, unit_id);
CREATE INDEX idx_leases_status ON leases(status);
CREATE INDEX idx_leases_end_date ON leases(end_date);

-- lease_tenants
CREATE TABLE lease_tenants (
  lease_id TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  role TEXT DEFAULT 'tenant',
  PRIMARY KEY (lease_id, tenant_id)
);

-- rent_payments
CREATE TABLE rent_payments (
  id TEXT PRIMARY KEY,
  lease_id TEXT NOT NULL,
  tenant_id TEXT,
  due_date TEXT NOT NULL,
  amount_due REAL NOT NULL,
  amount_paid REAL DEFAULT 0,
  payment_date TEXT,
  payment_method TEXT,
  status TEXT DEFAULT 'pending',
  reference TEXT,
  notes TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_rent_payments_lease_due ON rent_payments(lease_id, due_date);
CREATE INDEX idx_rent_payments_status ON rent_payments(status);

-- maintenance_requests
CREATE TABLE maintenance_requests (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL,
  unit_id TEXT,
  tenant_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  priority TEXT DEFAULT 'medium',
  category TEXT,
  status TEXT DEFAULT 'open',
  opened_at TEXT DEFAULT (datetime('now')),
  due_at TEXT,
  closed_at TEXT,
  cost_estimate REAL,
  cost_actual REAL,
  vendor_id TEXT
);
CREATE INDEX idx_maintenance_property ON maintenance_requests(property_id);
CREATE INDEX idx_maintenance_status ON maintenance_requests(status, priority);

-- vendors
CREATE TABLE vendors (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  contact_email TEXT,
  contact_phone TEXT,
  service_categories TEXT
);

-- property_expenses
CREATE TABLE property_expenses (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL,
  unit_id TEXT,
  vendor_id TEXT,
  description TEXT NOT NULL,
  category TEXT,
  amount REAL NOT NULL,
  expense_date TEXT NOT NULL,
  invoice_url TEXT,
  receipt_url TEXT,
  status TEXT DEFAULT 'recorded',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_expenses_property_date ON property_expenses(property_id, expense_date);

-- documents
CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL,
  unit_id TEXT,
  tenant_id TEXT,
  lease_id TEXT,
  title TEXT NOT NULL,
  doc_type TEXT,
  file_url TEXT NOT NULL,
  uploaded_at TEXT DEFAULT (datetime('now'))
);

-- hubs
CREATE TABLE hubs (
  id TEXT PRIMARY KEY,
  name TEXT,
  location TEXT,
  property_id TEXT,
  last_seen_at TEXT,
  status TEXT DEFAULT 'online'
);

-- devices
CREATE TABLE devices (
  id TEXT PRIMARY KEY,
  hub_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  domain TEXT,
  name TEXT,
  area TEXT,
  state TEXT,
  attributes TEXT,
  last_reported_at TEXT,
  UNIQUE(hub_id, entity_id)
);

-- device_syncs
CREATE TABLE device_syncs (
  id TEXT PRIMARY KEY,
  hub_id TEXT NOT NULL,
  sync_id TEXT NOT NULL,
  added INTEGER,
  updated INTEGER,
  removed INTEGER,
  created_at TEXT DEFAULT (datetime('now'))
);

-- commands
CREATE TABLE commands (
  id TEXT PRIMARY KEY,
  hub_id TEXT NOT NULL,
  target_entity TEXT NOT NULL,
  action TEXT NOT NULL,
  payload TEXT,
  status TEXT DEFAULT 'pending',
  issued_at TEXT DEFAULT (datetime('now')),
  executed_at TEXT,
  result TEXT
);

-- health_reports
CREATE TABLE health_reports (
  id TEXT PRIMARY KEY,
  hub_id TEXT NOT NULL,
  cpu_usage REAL,
  memory_usage REAL,
  disk_usage REAL,
  temperature REAL,
  services TEXT,
  reported_at TEXT DEFAULT (datetime('now'))
);
```

---

## Notes for Implementation

- When backend migrations are added, align column names/types with the inferred schema to keep Flutter DTOs stable. If the backend diverges, update this document and regenerate the Dart models.
- Prefer UUIDv4 across tables; keep them as strings in Flutter/SQLite.
- Add Alembic `server_default` timestamps and triggers for `updated_at` (or SQLAlchemy event listeners).
- For offline sync, track `updated_at` for conflict resolution and include soft-delete flags (`deleted_at`) if required by the mobile app.
- Consider PostGIS for geolocation (property centroid) if smart-building mapping is needed; not included here because no evidence was found in the repo.

---

## Outstanding Gap

The actual Alembic migration set is missing from the repository. Once available, re-run this documentation pass to capture authoritative table definitions, constraints, and indexes.
