# Contractors Module Documentation

**Feature**: Contractors Management
**Status**: ✅ Complete
**Version**: 1.0.0
**Last Updated**: December 2025

## Overview

The Contractors module provides comprehensive contractor management functionality for SomniProperty, including contractor profiles, performance tracking, labor time management, work order assignments, and rating systems.

## Architecture

The module follows Clean Architecture principles with clear separation of concerns:

```
lib/features/contractors/
├── domain/
│   ├── entities/          # Business entities
│   │   └── contractor.dart         # Contractor, Certification, Availability, LaborTime, etc.
│   ├── repositories/      # Repository interfaces
│   │   └── contractor_repository.dart
│   └── usecases/          # Business logic
│       ├── get_contractors.dart
│       ├── create_contractor.dart
│       ├── update_contractor.dart
│       ├── delete_contractor.dart
│       ├── assign_to_work_order.dart
│       ├── track_labor_time.dart
│       ├── rate_contractor.dart
│       ├── search_contractors.dart
│       └── get_contractor_performance.dart
├── data/
│   ├── datasources/       # API integration
│   │   └── contractor_remote_datasource.dart (18 endpoints)
│   ├── models/            # Data models
│   │   └── contractor_model.dart
│   └── repositories/      # Repository implementations
│       └── contractor_repository_impl.dart
└── presentation/
    ├── providers/         # State management
    │   └── contractor_provider.dart
    ├── screens/           # UI screens
    │   ├── contractors_list_screen.dart
    │   ├── contractor_detail_screen.dart
    │   └── contractor_form_screen.dart
    └── widgets/           # Reusable widgets
        ├── contractor_card.dart
        ├── contractor_stats_card.dart
        ├── contractor_rating_widget.dart
        └── contractor_performance_card.dart
```

## Domain Layer

### Entities

#### Contractor
Main entity representing a service provider/contractor.

**Fields**:
- `id`: String - Unique identifier
- `firstName`: String - Contractor's first name
- `lastName`: String - Contractor's last name
- `company`: String - Company name
- `email`: String - Contact email
- `phone`: String - Contact phone
- `specialty`: String - Main trade/specialty
- `status`: ContractorStatus - Active/Inactive/Suspended
- `hourlyRate`: double - Regular hourly rate
- `overtimeRate`: double - Overtime hourly rate
- `rating`: double - Average rating (0-5)
- `completedJobs`: int - Number of completed jobs
- `activeJobs`: int - Number of active jobs
- `skills`: List<String> - List of skills
- `certifications`: List<Certification> - Professional certifications
- `availability`: Availability? - Schedule availability
- `notes`: String? - Additional notes
- `profileImageUrl`: String? - Profile photo URL
- `createdAt`: DateTime - Creation timestamp
- `updatedAt`: DateTime - Last update timestamp

**Computed Properties**:
- `fullName`: String - Full name (firstName + lastName)
- `initials`: String - Initials for avatar
- `hasActiveJobs`: bool - Has active work orders
- `isAvailable`: bool - Currently available
- `formattedPhone`: String - Formatted phone number
- `averageRating`: double - Rating value
- `ratingStars`: int - Rating as integer
- `completionRate`: double - Job completion percentage
- `hasCertificationsExpiringSoon`: bool - Certifications expiring within 30 days
- `expiredCertifications`: List<Certification> - List of expired certifications

#### Certification
Professional certification information.

**Fields**:
- `name`: String - Certification name
- `issuingAuthority`: String? - Issuing organization
- `issueDate`: DateTime? - Issue date
- `expiryDate`: DateTime? - Expiration date
- `certificateNumber`: String? - Certificate number

**Computed Properties**:
- `isExpired`: bool - Certification has expired
- `isExpiringSoon`: bool - Expiring within 30 days
- `daysUntilExpiry`: int? - Days remaining

#### Availability
Work schedule and availability information.

**Fields**:
- `schedule`: Map<String, DayAvailability> - Weekly schedule
- `timeOff`: List<TimeOff> - Time off periods

**Computed Properties**:
- `isAvailableNow`: bool - Available at current time

#### LaborTime
Labor time tracking entry.

**Fields**:
- `id`: String - Unique identifier
- `contractorId`: String - Contractor reference
- `workOrderId`: String - Work order reference
- `date`: DateTime - Work date
- `hoursWorked`: double - Total hours worked
- `overtimeHours`: double - Overtime hours
- `regularCost`: double - Regular time cost
- `overtimeCost`: double - Overtime cost
- `totalCost`: double - Total cost
- `description`: String? - Work description
- `createdAt`: DateTime - Entry timestamp

#### ContractorPerformance
Performance metrics for a contractor.

**Fields**:
- `contractorId`: String - Contractor reference
- `averageRating`: double - Average rating
- `totalJobs`: int - Total jobs count
- `completedJobs`: int - Completed jobs count
- `activeJobs`: int - Active jobs count
- `averageCompletionTime`: double - Avg completion time (hours)
- `onTimePercentage`: double - On-time completion rate
- `totalRevenue`: double - Total revenue generated

#### ContractorRating
Rating/review for a contractor.

**Fields**:
- `id`: String - Unique identifier
- `contractorId`: String - Contractor reference
- `workOrderId`: String - Work order reference
- `rating`: int - Overall rating (1-5)
- `qualityRating`: int - Quality rating (1-5)
- `communicationRating`: int - Communication rating (1-5)
- `timelinessRating`: int - Timeliness rating (1-5)
- `review`: String? - Written review
- `reviewerName`: String? - Reviewer name
- `createdAt`: DateTime - Rating timestamp

### Repository Interface

`ContractorRepository` defines the following operations:

**CRUD Operations**:
- `getContractors({String? propertyId})`: Get all contractors
- `getContractor(String id)`: Get single contractor
- `createContractor(Contractor)`: Create new contractor
- `updateContractor(Contractor)`: Update contractor
- `deleteContractor(String id)`: Delete contractor

**Search & Filter**:
- `searchContractors(String query)`: Search by name/company
- `getContractorsBySpecialty(String)`: Filter by specialty
- `getContractorsByStatus(ContractorStatus)`: Filter by status
- `getAvailableContractors()`: Get available contractors

**Work Order Operations**:
- `assignToWorkOrder({...})`: Assign to work order
- `getContractorWorkOrders({...})`: Get contractor's work orders

**Labor Tracking**:
- `trackLaborTime({...})`: Record labor time
- `getLaborTimeEntries({...})`: Get labor entries

**Performance & Ratings**:
- `rateContractor({...})`: Rate contractor
- `getContractorRatings(String)`: Get ratings
- `getContractorPerformance(String)`: Get performance metrics

**Availability**:
- `updateAvailability({...})`: Update schedule

### Use Cases

All use cases follow the single responsibility principle:

- **GetContractors**: Retrieve contractor list
- **GetContractor**: Get single contractor details
- **CreateContractor**: Create new contractor
- **UpdateContractor**: Update contractor information
- **DeleteContractor**: Delete contractor
- **AssignToWorkOrder**: Assign contractor to work order
- **TrackLaborTime**: Record work hours
- **RateContractor**: Submit contractor rating
- **SearchContractors**: Search contractors
- **GetContractorPerformance**: Get performance metrics

## Data Layer

### Remote Data Source

`ContractorRemoteDataSource` implements **18 API endpoints**:

1. `GET /contractors` - List all contractors
2. `GET /contractors/:id` - Get contractor details
3. `POST /contractors` - Create contractor
4. `PUT /contractors/:id` - Update contractor
5. `DELETE /contractors/:id` - Delete contractor
6. `GET /contractors/search` - Search contractors
7. `GET /contractors?specialty=X` - Filter by specialty
8. `GET /contractors?status=X` - Filter by status
9. `GET /contractors/available` - Get available contractors
10. `POST /contractors/:id/assign` - Assign to work order
11. `GET /contractors/:id/work-orders` - Get work orders
12. `POST /contractors/:id/labor-time` - Track labor time
13. `GET /contractors/:id/labor-time` - Get labor entries
14. `POST /contractors/:id/ratings` - Rate contractor
15. `GET /contractors/:id/ratings` - Get ratings
16. `GET /contractors/:id/performance` - Get performance metrics
17. `PUT /contractors/:id/availability` - Update availability
18. `GET /contractors/stats` - Get statistics

### Models

**ContractorModel** extends Contractor entity with JSON serialization:

```dart
ContractorModel.fromJson(Map<String, dynamic>)  // Parse from API
ContractorModel.toJson()                         // Convert to JSON
ContractorModel.toCreateJson()                   // For POST requests
ContractorModel.fromEntity(Contractor)           // Convert from entity
ContractorModel.toEntity()                       // Convert to entity
```

Similar models exist for:
- `LaborTimeModel`
- `ContractorPerformanceModel`
- `ContractorRatingModel`
- `ContractorStatsModel`

### Repository Implementation

`ContractorRepositoryImpl` implements the repository interface with:
- Error handling (ServerException, NetworkException)
- Result wrapping (Either<Failure, T>)
- Entity/Model conversion

## Presentation Layer

### State Management

#### ContractorsProvider

Manages contractor list state using Riverpod StateNotifier:

**State**:
```dart
class ContractorsState {
  List<Contractor> contractors;
  bool isLoading;
  String? error;
  ContractorStatsModel? stats;
}
```

**Methods**:
- `loadContractors({String? propertyId})`
- `searchContractors(String query)`
- `filterByStatus(ContractorStatus)`
- `filterBySpecialty(String)`
- `loadAvailableContractors()`
- `createContractor(Contractor)` → bool
- `updateContractor(Contractor)` → bool
- `deleteContractor(String)` → bool
- `assignToWorkOrder({...})` → bool
- `trackLaborTime({...})` → bool
- `rateContractor({...})` → bool

#### ContractorDetailProvider

Manages single contractor detail state:

**State**:
```dart
class ContractorDetailState {
  Contractor? contractor;
  ContractorPerformance? performance;
  List<ContractorRating> ratings;
  List<LaborTime> laborTimeEntries;
  List<dynamic> workOrders;
  bool isLoading;
  String? error;
}
```

**Methods**:
- `loadContractor()`
- `refresh()`
- `updateAvailability(Availability)` → bool

### Screens

#### ContractorsListScreen

Main list view with:
- **Stats Cards**: Total, active, active jobs, avg rating
- **Search Bar**: Real-time search by name/company/specialty
- **Filters**: Status, specialty, availability
- **Contractor Cards**: Grid/list of contractors
- **FAB**: Add new contractor
- **Pull to Refresh**: Reload contractors

**Features**:
- Local client-side filtering
- Empty state handling
- Error state with retry
- Loading indicators

#### ContractorDetailScreen

Detailed contractor view with:
- **Profile Header**: Avatar, name, company, specialty, rating
- **Contact Info**: Email, phone with action buttons
- **Performance Metrics**: Jobs, completion time, on-time %, revenue
- **Skills & Certifications**: With expiry warnings
- **Labor Rates**: Regular and overtime rates
- **Active Jobs**: List of current work orders
- **Recent Ratings**: Rating history with reviews
- **Action Menu**: Assign, track time, rate
- **Edit/Delete**: Management actions

**Features**:
- Comprehensive contractor information
- Performance visualization
- Quick actions
- Refresh capability

#### ContractorFormScreen

Create/Edit form with:
- **Personal Info**: First name, last name, company
- **Contact**: Email, phone
- **Professional**: Specialty, status
- **Labor Rates**: Hourly, overtime
- **Skills**: Dynamic skill chips
- **Notes**: Additional information

**Features**:
- Form validation
- Status dropdown
- Skill management (add/remove)
- Rate inputs with currency formatting
- Create/Update modes

### Widgets

#### ContractorCard
Compact contractor display for lists:
- Avatar with initials fallback
- Name and company
- Status badge
- Specialty, rating, rate
- Active jobs indicator
- Edit/Delete actions

#### ContractorStatsCard
Statistics overview:
- Total contractors
- Active contractors
- Active jobs count
- Average rating

#### ContractorRatingWidget
Star rating display:
- Visual stars (full/half/empty)
- Numeric rating
- Completed jobs count

#### ContractorPerformanceCard
Performance metrics visualization:
- Total/completed jobs
- Average completion time
- On-time percentage
- Total revenue

## Business Logic

### Labor Cost Calculation

```dart
regularCost = regularHours × hourlyRate
overtimeCost = overtimeHours × overtimeRate
totalCost = regularCost + overtimeCost
```

### Rating Aggregation

Overall rating is calculated from multiple dimensions:
- Job quality
- Communication
- Timeliness
- Overall satisfaction

### Certification Expiry Warnings

- **Expired**: `expiryDate < now`
- **Expiring Soon**: `expiryDate < now + 30 days`
- Visual indicators (red/orange/green)

### Availability Checking

Checks:
1. Day of week availability
2. Time range (if specified)
3. Time-off periods

### Performance Metrics

Calculated metrics:
- **Completion Rate**: `completedJobs / totalJobs × 100`
- **Average Rating**: Mean of all ratings
- **On-Time %**: Jobs completed before deadline
- **Avg Completion Time**: Mean job duration

## API Integration

### Endpoint Mapping

All endpoints use the base URL from `ApiClient` with `/contractors` prefix:

```
Base: {API_URL}/v1/contractors
```

### Request/Response Format

**Create Contractor**:
```json
POST /contractors
{
  "first_name": "John",
  "last_name": "Smith",
  "company": "Smith Plumbing",
  "email": "john@example.com",
  "phone": "5551234567",
  "specialty": "Plumber",
  "status": "active",
  "hourly_rate": 75.00,
  "overtime_rate": 112.50,
  "skills": ["Plumbing", "Leak Repair"],
  "certifications": [...]
}
```

**Response**:
```json
{
  "id": "123",
  "first_name": "John",
  ...
  "rating": 4.5,
  "completed_jobs": 42,
  "active_jobs": 3,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

## Error Handling

All operations return `Either<Failure, T>`:

**Success**: `Right(value)`
**Failure**: `Left(failure)`

**Failure Types**:
- `ServerFailure`: API errors
- `NetworkFailure`: Connection issues
- `CacheFailure`: Local storage errors
- `ValidationFailure`: Input validation errors

## Testing Strategy

### Unit Tests

**Domain Layer**:
- Entity validation and computed properties
- Use case business logic
- Repository interface contracts

**Data Layer**:
- Model JSON serialization
- API endpoint integration
- Error handling and mapping

**Presentation Layer**:
- Provider state management
- Filter and search logic
- Form validation

### Widget Tests

- Screen rendering
- User interactions
- State updates
- Error states
- Loading states
- Empty states

### Integration Tests

- End-to-end flows
- API integration
- State persistence
- Navigation

## Usage Examples

### Creating a Contractor

```dart
final contractor = Contractor(
  id: '',
  firstName: 'John',
  lastName: 'Smith',
  company: 'Smith Plumbing',
  email: 'john@example.com',
  phone: '5551234567',
  specialty: 'Plumber',
  status: ContractorStatus.active,
  hourlyRate: 75.00,
  overtimeRate: 112.50,
  skills: ['Plumbing', 'Leak Repair'],
  createdAt: DateTime.now(),
  updatedAt: DateTime.now(),
);

final success = await ref
    .read(contractorsProvider.notifier)
    .createContractor(contractor);
```

### Tracking Labor Time

```dart
final success = await ref
    .read(contractorsProvider.notifier)
    .trackLaborTime(
      contractorId: '123',
      workOrderId: '456',
      date: DateTime.now(),
      hoursWorked: 8.0,
      overtimeHours: 2.0,
      description: 'Fixed water heater',
    );
```

### Rating a Contractor

```dart
final success = await ref
    .read(contractorsProvider.notifier)
    .rateContractor(
      contractorId: '123',
      workOrderId: '456',
      rating: 5,
      qualityRating: 5,
      communicationRating: 5,
      timelinessRating: 4,
      review: 'Excellent work!',
    );
```

## Future Enhancements

Potential improvements:
1. **Photo Upload**: Profile image management
2. **Document Storage**: Store certifications and licenses
3. **Calendar Integration**: Sync with external calendars
4. **Payment Integration**: Track payments and invoices
5. **Messaging**: In-app contractor communication
6. **Analytics**: Advanced performance analytics
7. **Recommendations**: AI-powered contractor matching
8. **Background Checks**: Integration with verification services
9. **Insurance Tracking**: Insurance policy management
10. **Equipment Tracking**: Tools and equipment management

## Performance Considerations

- **Lazy Loading**: Load details on demand
- **Caching**: Local cache for offline access
- **Pagination**: Support for large contractor lists
- **Debouncing**: Search input debouncing
- **Image Optimization**: Avatar image compression

## Accessibility

- Semantic labels for screen readers
- Sufficient color contrast
- Touch target sizes (44x44 minimum)
- Keyboard navigation support

## File Paths Reference

### Domain Layer
- `/lib/features/contractors/domain/entities/contractor.dart`
- `/lib/features/contractors/domain/repositories/contractor_repository.dart`
- `/lib/features/contractors/domain/usecases/*.dart`

### Data Layer
- `/lib/features/contractors/data/datasources/contractor_remote_datasource.dart`
- `/lib/features/contractors/data/models/contractor_model.dart`
- `/lib/features/contractors/data/repositories/contractor_repository_impl.dart`

### Presentation Layer
- `/lib/features/contractors/presentation/providers/contractor_provider.dart`
- `/lib/features/contractors/presentation/screens/contractors_list_screen.dart`
- `/lib/features/contractors/presentation/screens/contractor_detail_screen.dart`
- `/lib/features/contractors/presentation/screens/contractor_form_screen.dart`
- `/lib/features/contractors/presentation/widgets/*.dart`

## Conclusion

The Contractors module provides a complete, production-ready solution for contractor management with:
- ✅ Clean Architecture
- ✅ 18 API endpoints integrated
- ✅ Comprehensive UI with 3 screens
- ✅ Performance tracking
- ✅ Rating system
- ✅ Labor time tracking
- ✅ Advanced filtering and search
- ✅ Professional form validation
- ✅ Error handling
- ✅ State management

The module is ready for production use and follows Flutter/Dart best practices throughout.
