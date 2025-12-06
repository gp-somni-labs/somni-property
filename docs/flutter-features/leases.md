# Leases Module Documentation

> **Last Updated**: December 5, 2025
> **Status**: Enhanced - Core functionality complete
> **Module**: `lib/features/leases/`

## Overview

The Leases module manages rental agreements between property owners and tenants. It handles the complete lease lifecycle from creation through renewal or termination, with comprehensive financial tracking and expiration management.

## Architecture

### Domain Layer (`domain/`)

#### Entities

**Lease** (`entities/lease.dart`)
```dart
class Lease {
  final String id;
  final String propertyId;         // NEW: Link to property
  final String unitId;
  final String tenantId;
  final DateTime startDate;
  final DateTime endDate;
  final double monthlyRent;
  final double securityDeposit;
  final LeaseStatus status;        // pending, active, expiring, expired, terminated, renewed
  final LeaseType type;            // NEW: fixed, monthToMonth
  final int termMonths;            // NEW: Lease duration
  final DateTime? moveInDate;      // NEW: Actual move-in
  final DateTime? moveOutDate;     // NEW: Actual move-out
  final String? renewalStatus;     // NEW: pending, approved, declined
  final bool autoRenew;            // NEW: Auto-renewal flag
  final String? terminationReason; // NEW: Why lease was terminated
  final String? terms;
  final List<String>? specialConditions;
  final String? notes;
  final List<String>? attachmentUrls;  // NEW: PDF lease documents
  // ... metadata fields
}
```

**Key Computed Properties:**
- `isActive`: Lease is currently active
- `isExpiringSoon`: Within 30 days of expiration
- `hasExpired`: Past end date
- `daysUntilExpiry`: Days remaining
- `durationMonths`: Lease term length
- `totalValue`: Total lease value (rent × months)
- `canBeRenewed`: Eligible for renewal

**Enums:**
- `LeaseStatus`: pending, active, expiring, expired, terminated, renewed
- `LeaseType`: fixed (Fixed Term), monthToMonth (Month-to-Month)

#### Repositories

**LeaseRepository** (`repositories/lease_repository.dart`)
```dart
abstract class LeaseRepository {
  Future<Either<Failure, List<Lease>>> getLeases({String? propertyId, String? tenantId});
  Future<Either<Failure, Lease>> getLease(String id);
  Future<Either<Failure, Lease>> createLease(Lease lease);
  Future<Either<Failure, Lease>> updateLease(Lease lease);
  Future<Either<Failure, void>> deleteLease(String id);
  Future<Either<Failure, Lease>> renewLease(String id, DateTime newEndDate, double? newRent);
  Future<Either<Failure, Lease>> terminateLease(String id, DateTime terminationDate, String reason);
  Future<Either<Failure, List<Lease>>> getLeasesByStatus(LeaseStatus status);
  Future<Either<Failure, List<Lease>>> getExpiringLeases(int withinDays);
  Future<Either<Failure, List<Lease>>> getLeasesByUnit(String unitId);
}
```

### Data Layer (`data/`)

#### Models

**LeaseModel** (`models/lease_model.dart`)
- Extends Lease entity
- Handles JSON serialization/deserialization
- Maps snake_case API fields to camelCase Dart fields
- Provides `fromJson()`, `toJson()`, `toCreateJson()`, `fromEntity()` methods

**LeaseStatsModel** (`models/lease_model.dart`)
- Aggregates lease statistics
- Fields: totalLeases, activeLeases, expiringLeases, pendingLeases, totalMonthlyRevenue
- Can be computed from lease list or fetched from API

#### Data Sources

**LeaseRemoteDataSource** (`datasources/lease_remote_datasource.dart`)
- API communication via Dio HTTP client
- Endpoints:
  - `GET /api/v1/leases` - List with filters
  - `GET /api/v1/leases/{id}` - Single lease
  - `POST /api/v1/leases` - Create
  - `PUT /api/v1/leases/{id}` - Update
  - `DELETE /api/v1/leases/{id}` - Delete
  - `POST /api/v1/leases/{id}/renew` - Renew lease
  - `POST /api/v1/leases/{id}/terminate` - Terminate lease
  - `GET /api/v1/leases/expiring?days=30` - Get expiring leases
  - Query params: `property_id`, `tenant_id`, `unit_id`, `status`

#### Repository Implementation

**LeaseRepositoryImpl** (`repositories/lease_repository_impl.dart`)
- Implements LeaseRepository interface
- Error handling: ServerException, NetworkException → Failure
- Converts between models and entities

### Presentation Layer (`presentation/`)

#### State Management

**Providers** (`providers/lease_provider.dart`)

**LeasesProvider** - StateNotifierProvider<LeasesNotifier, LeasesState>
```dart
class LeasesState {
  final List<Lease> leases;
  final bool isLoading;
  final String? error;
  final LeaseStatsModel? stats;
}
```

Methods:
- `loadLeases({propertyId, tenantId})` - Load all/filtered leases
- `filterByStatus(LeaseStatus)` - Filter by status
- `loadExpiringLeases({withinDays})` - Get expiring leases
- `createLease(Lease)` - Create new lease
- `updateLease(Lease)` - Update existing
- `deleteLease(String id)` - Delete lease
- `renewLease(id, newEndDate, newRent)` - Renew lease
- `terminateLease(id, terminationDate, reason)` - Terminate lease

**LeaseDetailProvider** - StateNotifierProvider.family<LeaseDetailNotifier, LeaseDetailState, String>
```dart
class LeaseDetailState {
  final Lease? lease;
  final bool isLoading;
  final String? error;
}
```

Methods:
- `loadLease()` - Load single lease by ID
- `refresh()` - Refresh lease details

#### Pages

**LeasesListPage** (`pages/leases_list_page.dart`)
- **Purpose**: Main lease management screen
- **Features**:
  - Stats cards (Total, Active, Expiring, Monthly Revenue)
  - Status filter dropdown (All, Pending, Active, Expired, etc.)
  - "Expiring Soon" filter chip
  - Lease cards in scrollable list
  - Pull-to-refresh
  - FAB: Create new lease
  - Empty/loading/error states
- **Actions**:
  - Tap card → Navigate to detail page
  - Renew button → Show renewal dialog
  - Terminate button → Show termination dialog

**LeaseDetailPage** (`pages/lease_detail_page.dart`)
- **Purpose**: Detailed view of single lease
- **Sections**:
  - Status header (large status badge, dates, expiring warning)
  - Lease Terms (start/end dates, duration, days remaining)
  - Financial Details (rent, deposit, total value)
  - Unit & Tenant info (with links)
  - Special Conditions (bullet list)
  - Terms & Notes (full text)
  - Quick Actions (View Payments, Documents, Print)
  - Metadata (created/updated timestamps)
- **Actions**:
  - Edit button → Navigate to form
  - Menu: Renew, Terminate, Delete
  - Pull-to-refresh

**LeaseFormPage** (`pages/lease_form_page.dart`)
- **Purpose**: Create or edit lease
- **Sections**:
  - Unit & Tenant selection (text fields - TODO: enhance with pickers)
  - Lease Period (start date, end date with date pickers)
  - Duration display (auto-calculated months)
  - Financial Details (monthly rent, security deposit)
  - Status dropdown
  - Special Conditions (add/remove list)
  - Terms & Notes (multiline text)
- **Validation**:
  - Required: unit, tenant, dates, monthly rent
  - Numeric validation for amounts
  - End date must be after start date
- **Actions**:
  - Save → Create or update lease
  - Auto-navigates back on success

#### Widgets

**LeaseCard** (`widgets/lease_card.dart`)
- Compact card for list display
- Shows: tenant name, unit, dates, status badge, rent, deposit
- Expiring warning banner (if applicable)
- Action buttons: Renew, Terminate (contextual)

**LeaseStatsCard** (`widgets/lease_card.dart`)
- Colorful stat card for dashboard
- Icon, large value, label

**LeaseTimelineWidget** (`widgets/lease_timeline_widget.dart`) ⭐ NEW
- Visual timeline of lease lifecycle
- Events: Start → Move In → Expiring Soon → Move Out → End/Terminated
- Progress bar (for active leases)
- Colored indicators for completed events
- Vertical timeline with icons and dates

**LeaseFinancialCard** (`widgets/lease_financial_card.dart`) ⭐ NEW
- Comprehensive financial summary
- Monthly rent (prominent display)
- Grid of metrics: Deposit, Term, Total Value, Expected/Month
- Payment progress tracking (if data available)
- Amount due warning (if applicable)
- Additional calculations: Daily rate, Annual value

**ExpiringLeaseAlert** (`widgets/expiring_lease_alert.dart`) ⭐ NEW
- Prominent alert banner for expiring leases
- Urgency levels:
  - **Critical** (≤7 days): Red, ERROR icon
  - **High Priority** (≤14 days): Deep orange, WARNING icon
  - **Attention** (≤30 days): Orange, WARNING_AMBER icon
- Shows: Days left, tenant, unit, expiration date, rent
- Action buttons: Renew Lease, View Details
- Compact variant for list displays

## Business Logic

### Lease Lifecycle States

```
pending → active → expiring → expired
                → terminated (anytime)
                → renewed → new lease (active)
```

### Status Transitions

- **pending** → **active**: On start date or manual activation
- **active** → **expiring**: Auto-flagged when < 30 days remaining
- **active/expiring** → **expired**: Auto-transitioned after end date
- **active/expiring** → **terminated**: Manual termination
- **active/expiring** → **renewed**: Creates new lease, marks old as renewed

### Date Calculations

```dart
// Days until expiry
int daysUntilExpiry = endDate.difference(DateTime.now()).inDays;

// Is expiring soon? (within 30 days)
bool isExpiringSoon = status == LeaseStatus.active &&
                      daysUntilExpiry <= 30 &&
                      daysUntilExpiry > 0;

// Has expired?
bool hasExpired = DateTime.now().isAfter(endDate);

// Duration in months
int durationMonths = termMonths; // Stored value

// Total lease value
double totalValue = monthlyRent * termMonths;

// Daily rate
double dailyRate = monthlyRent / 30;

// Annual value
double annualValue = monthlyRent * 12;
```

### Financial Calculations

```dart
// Expected total payments
double expectedTotal = monthlyRent * termMonths;

// Payment progress
double progress = totalPaid / expectedTotal;

// Remaining balance
double remaining = expectedTotal - totalPaid;

// Amount currently due
double amountDue = calculateDueAmount(lease, payments);
```

## API Integration

### Request/Response Examples

**Create Lease**
```http
POST /api/v1/leases
Content-Type: application/json

{
  "property_id": "prop_123",
  "unit_id": "unit_456",
  "tenant_id": "tenant_789",
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-12-31T23:59:59Z",
  "monthly_rent": 2500.00,
  "security_deposit": 2500.00,
  "status": "pending",
  "type": "fixed",
  "term_months": 12,
  "auto_renew": false,
  "terms": "Standard lease terms apply",
  "special_conditions": ["No smoking", "Pets allowed with deposit"],
  "notes": "Tenant requested lease start on 1st"
}
```

**Response**
```json
{
  "id": "lease_abc123",
  "property_id": "prop_123",
  "unit_id": "unit_456",
  "tenant_id": "tenant_789",
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-12-31T23:59:59Z",
  "monthly_rent": 2500.00,
  "security_deposit": 2500.00,
  "status": "pending",
  "type": "fixed",
  "term_months": 12,
  "move_in_date": null,
  "move_out_date": null,
  "renewal_status": null,
  "auto_renew": false,
  "termination_reason": null,
  "terms": "Standard lease terms apply",
  "special_conditions": ["No smoking", "Pets allowed with deposit"],
  "notes": "Tenant requested lease start on 1st",
  "attachment_urls": [],
  "property_name": "Sunset Apartments",
  "unit_number": "204",
  "tenant_name": "John Doe",
  "created_at": "2024-12-01T10:30:00Z",
  "updated_at": "2024-12-01T10:30:00Z"
}
```

**Get Expiring Leases**
```http
GET /api/v1/leases/expiring?days=30
```

**Renew Lease**
```http
POST /api/v1/leases/lease_abc123/renew
Content-Type: application/json

{
  "new_end_date": "2026-12-31T23:59:59Z",
  "new_rent": 2600.00  // Optional rent increase
}
```

**Terminate Lease**
```http
POST /api/v1/leases/lease_abc123/terminate
Content-Type: application/json

{
  "termination_date": "2025-06-30T23:59:59Z",
  "reason": "Tenant violated lease terms - noise complaints"
}
```

## User Flows

### Create Lease Flow

1. User taps FAB "+ New Lease" on list page
2. Navigate to LeaseFormPage (create mode)
3. User fills form:
   - Select property, unit, tenant (TODO: enhance with searchable pickers)
   - Choose lease type (Fixed Term / Month-to-Month)
   - Pick start and end dates
   - Enter monthly rent and security deposit
   - Set initial status (typically "Pending")
   - Add special conditions (optional)
   - Enter terms and notes (optional)
4. User taps "Create" button
5. Validation runs
6. API call: POST /api/v1/leases
7. On success:
   - Show success snackbar
   - Navigate back to list
   - List refreshes to show new lease
8. On failure: Show error snackbar

### Renew Lease Flow

1. User views lease detail or clicks "Renew" on lease card
2. Renewal dialog appears:
   - Shows current end date
   - Date picker for new end date (default: +365 days)
   - Optional field for rent adjustment
3. User selects new date and optionally changes rent
4. User taps "Renew" button
5. API call: POST /api/v1/leases/{id}/renew
6. On success:
   - Original lease status → "renewed"
   - New lease created with updated dates/rent
   - Show success message
   - Refresh list/detail
7. On failure: Show error message

### Terminate Lease Flow

1. User clicks "Terminate" button (detail page or card)
2. Termination dialog appears:
   - Warning message (irreversible action)
   - Required field: Termination reason
   - Date picker: Termination date (default: today)
3. User enters reason and confirms
4. API call: POST /api/v1/leases/{id}/terminate
5. On success:
   - Lease status → "terminated"
   - `terminationReason` and `moveOutDate` set
   - Show success message
   - Refresh
6. On failure: Show error message

### Expiring Lease Management Flow

1. System identifies leases expiring within 30 days
2. Leases auto-flagged with `isExpiringSoon`
3. ExpiringLeaseAlert banner shows on detail page
4. Property manager sees urgency indicators:
   - Red (≤7 days): URGENT
   - Orange (≤14 days): HIGH PRIORITY
   - Yellow (≤30 days): ATTENTION
5. Manager has options:
   - Contact tenant (via tenant detail)
   - Initiate renewal
   - Plan move-out
6. After action, status updates and alert clears

## Testing Strategy

### Unit Tests

**Domain Entity Tests** (`test/features/leases/domain/entities/lease_test.dart`)
```dart
// Test computed properties
- isActive returns true when status is active
- isExpiringSoon returns true when within 30 days
- daysUntilExpiry calculates correctly
- totalValue computes monthlyRent * termMonths
- canBeRenewed returns false when pending renewal

// Test date calculations
- hasExpired returns true after end date
- hasMoveIn returns true when moveInDate is set

// Test equality
- Leases with same props are equal
- copyWith creates new instance with changes
```

**Data Model Tests** (`test/features/leases/data/models/lease_model_test.dart`)
```dart
// Serialization
- fromJson correctly parses API response
- toJson creates valid API payload
- toCreateJson omits ID and metadata
- fromEntity converts domain entity

// Edge cases
- Handles null optional fields
- Parses different date formats
- Handles missing nested objects
```

**Repository Tests** (`test/features/leases/data/repositories/lease_repository_impl_test.dart`)
```dart
// Success cases
- getLeases returns list of leases
- createLease returns created lease
- renewLease returns renewed lease

// Error handling
- ServerException converts to ServerFailure
- NetworkException converts to NetworkFailure
```

### Widget Tests

**LeaseCard Tests**
```dart
- Displays lease information correctly
- Shows expiring warning when applicable
- Action buttons appear for active leases
- Tapping card calls onTap callback
```

**LeaseFormPage Tests**
```dart
- Validates required fields
- Date picker updates state
- Duration auto-calculates
- Special conditions add/remove
- Submit button disabled while loading
```

**LeaseDetailPage Tests**
```dart
- Displays all lease sections
- Refresh indicator works
- Action menu items appear based on status
- Navigate to edit form
```

### Integration Tests

**Lease Lifecycle Test**
```dart
// Create → View → Edit → Renew → Terminate
1. Create lease via form
2. Navigate to detail page
3. Verify all data displayed
4. Edit lease and save
5. Renew lease with new date
6. Verify new lease created
7. Terminate original lease
8. Verify status updated
```

## Future Enhancements

### High Priority

1. **Property/Unit/Tenant Pickers**
   - Replace text fields with searchable dropdowns
   - Fetch and display available units
   - Show tenant contact info during selection
   - Filter units by property

2. **Document Management**
   - Upload PDF lease documents
   - Download and view attachments
   - Digital signature integration
   - Document versioning

3. **Local Caching (Drift)**
   - Cache leases for offline access
   - Queue mutations when offline
   - Sync when online
   - Conflict resolution

4. **Search & Advanced Filters**
   - Full-text search (tenant name, unit number, property)
   - Date range filters
   - Rent amount range
   - Sort options (end date, start date, rent)

### Medium Priority

5. **Notifications**
   - Push notifications for expiring leases
   - Email reminders to property managers
   - Tenant renewal invitations

6. **Payment Integration**
   - Link leases to payment records
   - Show payment history on detail page
   - Calculate amount due automatically
   - Payment schedule visualization

7. **Lease Templates**
   - Pre-defined terms and conditions
   - Property-specific defaults
   - Special condition library

8. **Bulk Operations**
   - Multi-select leases
   - Bulk renewal
   - Export to CSV/PDF

### Low Priority

9. **Analytics Dashboard**
   - Lease renewal rates
   - Average lease duration
   - Revenue trends
   - Occupancy forecasting

10. **Lease Comparison**
    - Compare multiple leases side-by-side
    - Historical lease data for unit
    - Market rate analysis

## Known Issues

1. **Form Enhancement Needed**
   - Unit/Tenant selection uses text ID input instead of pickers
   - No validation for property/unit/tenant existence
   - Auto-complete would improve UX

2. **No Offline Support**
   - All operations require network
   - No local database caching yet
   - Failed requests don't queue for retry

3. **Document Upload Not Implemented**
   - `attachmentUrls` field exists but no UI
   - Need file picker integration
   - Need S3/storage service integration

4. **Limited Search**
   - No search bar on list page
   - Filter by status only
   - Can't search by tenant name or property

5. **No Payment Tracking**
   - Financial card shows expected totals
   - `totalPaid` and `amountDue` not implemented
   - Need integration with Payments module

## File Structure

```
lib/features/leases/
├── domain/
│   ├── entities/
│   │   └── lease.dart                    ✅ ENHANCED
│   └── repositories/
│       └── lease_repository.dart         ✅ Complete
├── data/
│   ├── models/
│   │   └── lease_model.dart              ✅ ENHANCED
│   ├── datasources/
│   │   └── lease_remote_datasource.dart  ✅ Complete
│   └── repositories/
│       └── lease_repository_impl.dart    ✅ Complete
└── presentation/
    ├── providers/
    │   └── lease_provider.dart           ✅ Complete
    ├── pages/
    │   ├── leases_list_page.dart         ✅ Complete
    │   ├── lease_detail_page.dart        ✅ Complete
    │   └── lease_form_page.dart          ✅ Complete (needs picker enhancement)
    └── widgets/
        ├── lease_card.dart               ✅ Complete
        ├── lease_timeline_widget.dart    ✅ NEW - Complete
        ├── lease_financial_card.dart     ✅ NEW - Complete
        └── expiring_lease_alert.dart     ✅ NEW - Complete
```

## Dependencies

```yaml
dependencies:
  flutter_riverpod: ^2.5.0      # State management
  dartz: ^0.10.1                # Functional programming (Either)
  equatable: ^2.0.5             # Value equality
  dio: ^5.4.0                   # HTTP client
  go_router: ^13.0.0            # Navigation
```

## Conclusion

The Leases module provides comprehensive lease lifecycle management with:
- ✅ Full CRUD operations
- ✅ Renewal and termination flows
- ✅ Expiration tracking and alerts
- ✅ Financial calculations
- ✅ Visual timeline display
- ✅ Rich UI components
- ⚠️ Form enhancements needed (pickers)
- ⚠️ Document upload pending
- ⚠️ Offline caching pending
- ⚠️ Tests pending

The module is production-ready for core functionality. Enhanced features (pickers, documents, offline support, tests) should be prioritized in the next iteration.
