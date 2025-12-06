# Dashboard Feature Documentation

**Feature**: Dashboard
**Status**: ✅ Complete
**Priority**: P0 (Critical - Landing Page)
**Last Updated**: December 2024

## Overview

The Dashboard is the primary landing page after authentication, providing users with a comprehensive overview of their property management operations. It displays real-time statistics, charts, activity feeds, and urgent alerts.

## Architecture

### Layer Structure

```
dashboard/
├── domain/
│   ├── entities/          # Business entities
│   │   ├── dashboard_stats.dart
│   │   ├── activity_item.dart
│   │   └── alert.dart
│   └── repositories/      # Repository interfaces
│       └── dashboard_repository.dart
├── data/
│   ├── models/            # Data models with JSON serialization
│   │   ├── dashboard_stats_model.dart
│   │   ├── activity_item_model.dart
│   │   └── alert_model.dart
│   ├── datasources/       # API clients
│   │   └── dashboard_remote_datasource.dart
│   └── repositories/      # Repository implementations
│       └── dashboard_repository_impl.dart
└── presentation/
    ├── pages/             # Pages/screens
    │   └── dashboard_page.dart
    ├── providers/         # State management
    │   └── dashboard_provider.dart
    └── widgets/           # Reusable widgets
        ├── dashboard_stat_card.dart
        ├── revenue_chart.dart
        ├── occupancy_chart.dart
        ├── activity_feed.dart
        ├── alerts_banner.dart
        └── dashboard_loading_shimmer.dart
```

## Backend API Endpoints

The Dashboard integrates with the following backend endpoints:

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/v1/dashboard/stats` | GET | Overall statistics | `DashboardStats` |
| `/api/v1/dashboard/revenue` | GET | Revenue trend data (12 months) | `List<RevenueData>` |
| `/api/v1/dashboard/occupancy` | GET | Occupancy statistics | `OccupancyStats` |
| `/api/v1/dashboard/work-orders` | GET | Work order metrics | `WorkOrderStats` |
| `/api/v1/dashboard/activity` | GET | Recent activity feed (limit: 20) | `List<ActivityItem>` |
| `/api/v1/dashboard/alerts` | GET | Urgent alerts | `List<Alert>` |
| `/api/v1/dashboard/upcoming` | GET | Upcoming events (30 days) | `List<UpcomingEvent>` |
| `/api/v1/dashboard/alerts/:id/dismiss` | POST | Dismiss an alert | `void` |

### Query Parameters

- **Revenue**: `?months=12` - Number of months to retrieve
- **Activity**: `?limit=20` - Number of activities to retrieve
- **Upcoming**: `?days=30` - Number of days ahead to retrieve

## Domain Entities

### DashboardStats

Core statistics displayed in stat cards.

```dart
class DashboardStats {
  final int totalProperties;
  final int activeTenants;
  final double monthlyRevenue;
  final int openWorkOrders;
  final int availableUnits;
  final double overduePayments;
  final double occupancyRate;
  final TrendIndicator propertyTrend;
  final TrendIndicator tenantTrend;
  final TrendIndicator revenueTrend;
}

enum TrendIndicator { up, down, neutral }
```

### RevenueData

Monthly revenue data for charts.

```dart
class RevenueData {
  final DateTime month;
  final double amount;
  final double? projected;  // Optional projected revenue
}
```

### OccupancyStats

Occupancy information for donut chart.

```dart
class OccupancyStats {
  final int totalUnits;
  final int occupiedUnits;
  final int availableUnits;
  final double occupancyRate;
}
```

### WorkOrderStats

Work order status breakdown.

```dart
class WorkOrderStats {
  final int openCount;
  final int inProgressCount;
  final int completedCount;
  final int criticalCount;

  int get total => openCount + inProgressCount + completedCount;
}
```

### ActivityItem

Recent activity with contextual information.

```dart
class ActivityItem {
  final String id;
  final String title;
  final String description;
  final ActivityType type;
  final DateTime timestamp;
  final String? userId;
  final String? userName;
  final String? relatedEntityId;
  final String? relatedEntityType;

  String get timeAgo;      // "2 hours ago"
  String get dateGroup;    // "Today", "Yesterday", etc.
}

enum ActivityType {
  propertyCreated, propertyUpdated,
  tenantAdded, tenantRemoved,
  leaseCreated, leaseExpiring, leaseRenewed,
  paymentReceived, paymentOverdue,
  workOrderCreated, workOrderCompleted,
  maintenanceScheduled, documentUploaded,
  userActivity, systemAlert
}
```

### Alert

Urgent notifications requiring attention.

```dart
class Alert {
  final String id;
  final String title;
  final String message;
  final AlertPriority priority;
  final AlertType type;
  final DateTime createdAt;
  final String? actionUrl;
  final String? actionLabel;
  final bool isDismissible;

  String? get timeRemaining;  // For time-sensitive alerts
}

enum AlertPriority { critical, high, medium, low }

enum AlertType {
  leaseExpiring, paymentDue, paymentOverdue,
  maintenanceRequired, maintenanceScheduled,
  workOrderCritical, documentExpiring,
  inspectionDue, complianceIssue, systemNotification
}
```

### UpcomingEvent

Scheduled events for planning.

```dart
class UpcomingEvent {
  final String id;
  final String title;
  final String description;
  final DateTime scheduledDate;
  final EventType type;

  int get daysUntil;
}

enum EventType {
  leaseRenewal, inspection, maintenance,
  payment, meeting, other
}
```

## State Management

### DashboardProvider

Manages all dashboard state with Riverpod.

```dart
final dashboardProvider = StateNotifierProvider<DashboardNotifier, DashboardState>((ref) {
  return DashboardNotifier(repository: ref.watch(dashboardRepositoryProvider));
});
```

### DashboardState

```dart
class DashboardState {
  final DashboardStats? stats;
  final List<RevenueData> revenue;
  final OccupancyStats? occupancy;
  final WorkOrderStats? workOrders;
  final List<ActivityItem> activity;
  final List<Alert> alerts;
  final List<UpcomingEvent> upcomingEvents;
  final bool isLoading;
  final String? error;
  final DateTime? lastRefresh;

  bool get isEmpty;
  bool get needsRefresh;  // True if > 5 minutes old
  Map<String, List<ActivityItem>> get groupedActivities;
  List<Alert> getAlertsByPriority(AlertPriority priority);
}
```

### Key Methods

- **`loadAllData()`**: Fetches all dashboard data in parallel (initial load)
- **`refresh()`**: Manually refresh all data
- **`loadStats()`**: Refresh only statistics (lighter operation)
- **`loadActivity()`**: Refresh only activity feed
- **`loadAlerts()`**: Refresh only alerts
- **`dismissAlert(alertId)`**: Dismiss a specific alert

### Auto-Refresh

The dashboard automatically refreshes every 5 minutes when the `lastRefresh` timestamp is older than 5 minutes.

## UI Components

### 1. Stats Cards (6 Cards)

Displays key metrics in a responsive grid.

**Cards**:
1. **Total Properties** - Count with trend indicator
2. **Active Tenants** - Count with occupancy % subtitle
3. **Monthly Revenue** - Currency formatted with trend
4. **Open Work Orders** - Count with critical count subtitle
5. **Available Units** - Count with "of X total" subtitle
6. **Overdue Payments** - Currency formatted (red if > 0)

**Features**:
- Trend indicators (up/down/neutral) with percentage change
- Color-coded icons
- Tappable to navigate to respective module
- Responsive grid (2-4 columns based on screen width)

### 2. Revenue Chart (Line Chart)

Displays monthly revenue trend using `fl_chart`.

**Features**:
- 12-month historical data
- Curved line with gradient fill
- Projected revenue (dashed line) if available
- Interactive tooltips on touch
- Responsive scaling (K/M formatting)
- Month labels on X-axis

### 3. Occupancy Chart (Donut Chart)

Visual representation of unit occupancy.

**Features**:
- Center displays occupancy percentage
- Occupied units (primary color)
- Available units (surface color)
- Legend with unit counts
- Responsive sizing

### 4. Work Order Chart (Bar Chart)

Status breakdown of work orders.

**Features**:
- Three bars: Open, In Progress, Completed
- Color-coded (orange, blue, green)
- Interactive tooltips
- Horizontal grid lines

### 5. Activity Feed

Recent activities grouped by date.

**Features**:
- Groups: "Today", "Yesterday", "This Week", "Earlier"
- Activity type icons with color coding
- Timestamp relative ("2 hours ago")
- Tappable to view details
- Maximum 20 items
- Empty state when no activities

**Activity Types & Icons**:
- Properties: apartment (blue)
- Tenants: people (green)
- Leases: description (orange)
- Payments: check_circle (green) / warning (red)
- Work Orders: build (purple)
- Maintenance: schedule (teal)
- Documents: upload_file (indigo)
- Alerts: notifications (amber)

### 6. Alerts Banner

Urgent notifications at top of dashboard.

**Features**:
- Shows only critical & high priority alerts (max 3)
- Color-coded by priority (red/orange/yellow/blue)
- Dismissible cards
- Action buttons ("View", "Dismiss")
- Time remaining indicator for time-sensitive alerts
- Priority badges
- Empty state: hidden when no urgent alerts

### 7. Loading States

**Shimmer Loading**:
- Animated shimmer effect on skeleton UI
- Grid of card placeholders
- Chart placeholders
- Activity feed placeholder

**Error State**:
- Error icon and message
- "Retry" button
- Centered layout

**Empty State**:
- Welcome message
- Subtitle with guidance
- Call-to-action button
- Dashboard icon

## User Interactions

### Pull-to-Refresh

Swipe down from top to manually refresh all dashboard data.

```dart
RefreshIndicator(
  onRefresh: () async {
    await ref.read(dashboardProvider.notifier).refresh();
  },
  child: _buildBody(context, ref, dashboardState, user),
)
```

### Quick Actions FAB

Floating Action Button with speed dial menu.

**Actions**:
1. Add Property
2. Add Tenant
3. Create Lease
4. Record Payment
5. Create Work Order

Opens as a bottom sheet with list of actions.

### Card Navigation

Stat cards are tappable and navigate to respective modules:
- Properties → `/properties`
- Tenants → `/tenants`
- Leases → `/leases`
- Work Orders → `/work-orders`
- Payments → `/payments`

## Performance Optimizations

### Parallel Data Loading

All dashboard endpoints are called in parallel using `Future.wait()`:

```dart
Future<Either<Failure, DashboardData>> getAllData() async {
  final results = await Future.wait([
    remoteDataSource.getStats(),
    remoteDataSource.getRevenue(months: 12),
    remoteDataSource.getOccupancy(),
    remoteDataSource.getWorkOrders(),
    remoteDataSource.getActivity(limit: 20),
    remoteDataSource.getAlerts(),
    remoteDataSource.getUpcoming(days: 30),
  ]);

  return Right(DashboardData(...));
}
```

### Caching Strategy

- Last refresh timestamp tracked
- Auto-refresh only if > 5 minutes old
- Manual refresh available via pull-to-refresh or refresh button

### Incremental Updates

Lighter methods available for updating specific sections:
- `loadStats()` - Refresh only stats cards
- `loadActivity()` - Refresh only activity feed
- `loadAlerts()` - Refresh only alerts

## Responsive Design

### Breakpoints

- **Mobile** (< 600px): 2-column stats grid, vertical charts
- **Tablet** (600-800px): 3-column stats grid, vertical charts
- **Desktop** (800-1200px): 3-column stats grid, horizontal charts
- **Large Desktop** (> 1200px): 4-column stats grid, horizontal charts

### Adaptive Layouts

```dart
if (MediaQuery.of(context).size.width > 800)
  _buildChartsRow(context, dashboardState)  // Side-by-side
else
  _buildChartsColumn(context, dashboardState)  // Stacked
```

## Testing

### Unit Tests

Located in `test/features/dashboard/data/models/`

**Coverage**:
- Model JSON serialization/deserialization
- Trend indicator parsing
- Occupancy rate calculation
- Work order totals
- Edge cases (missing fields, null values)

### Widget Tests

Located in `test/features/dashboard/presentation/widgets/`

**Coverage**:
- Stat card rendering
- Trend indicator display
- Subtitle display
- Tap interactions
- Grid layout with different stats

### Integration Tests

**Scenarios**:
1. Initial load from empty state
2. Pull-to-refresh functionality
3. Error handling and retry
4. Alert dismissal
5. Navigation from stat cards
6. Quick actions menu

## Error Handling

### Network Errors

- Display error state with retry button
- Preserve previously loaded data if available
- Toast notification for background refresh failures

### Empty Data

- Show appropriate empty states
- Guide user to add first property
- Hide sections with no data (e.g., no alerts)

### API Failures

- Graceful degradation (show partial data)
- Error messages from backend
- Fallback to cached data if recent

## Future Enhancements

### Phase 2
- [ ] Customizable dashboard widgets
- [ ] Widget reordering/hiding
- [ ] Drill-down from charts
- [ ] Export dashboard report (PDF)
- [ ] Date range selector for charts
- [ ] Comparison views (YoY, MoM)

### Phase 3
- [ ] Real-time updates (WebSocket)
- [ ] Push notifications for critical alerts
- [ ] Dashboard themes/layouts
- [ ] Saved dashboard configurations
- [ ] Multi-property filtering
- [ ] Advanced analytics integration

## Dependencies

```yaml
dependencies:
  flutter_riverpod: ^2.4.9      # State management
  go_router: ^13.0.0            # Navigation
  fl_chart: ^0.66.0             # Charts
  intl: ^0.18.1                 # Formatting
  shimmer: ^3.0.0               # Loading states
  dio: ^5.4.0                   # HTTP client
  dartz: ^0.10.1                # Functional programming
```

## File Paths

### Domain Layer
- `/lib/features/dashboard/domain/entities/dashboard_stats.dart`
- `/lib/features/dashboard/domain/entities/activity_item.dart`
- `/lib/features/dashboard/domain/entities/alert.dart`
- `/lib/features/dashboard/domain/repositories/dashboard_repository.dart`

### Data Layer
- `/lib/features/dashboard/data/models/dashboard_stats_model.dart`
- `/lib/features/dashboard/data/models/activity_item_model.dart`
- `/lib/features/dashboard/data/models/alert_model.dart`
- `/lib/features/dashboard/data/datasources/dashboard_remote_datasource.dart`
- `/lib/features/dashboard/data/repositories/dashboard_repository_impl.dart`

### Presentation Layer
- `/lib/features/dashboard/presentation/pages/dashboard_page.dart`
- `/lib/features/dashboard/presentation/providers/dashboard_provider.dart`
- `/lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart`
- `/lib/features/dashboard/presentation/widgets/revenue_chart.dart`
- `/lib/features/dashboard/presentation/widgets/occupancy_chart.dart`
- `/lib/features/dashboard/presentation/widgets/activity_feed.dart`
- `/lib/features/dashboard/presentation/widgets/alerts_banner.dart`
- `/lib/features/dashboard/presentation/widgets/dashboard_loading_shimmer.dart`

### Tests
- `/test/features/dashboard/data/models/dashboard_stats_model_test.dart`
- `/test/features/dashboard/presentation/widgets/dashboard_stat_card_test.dart`

## Known Issues

None currently. All P0 features implemented and tested.

## Change Log

### v1.0.0 (December 2024)
- Initial implementation of complete dashboard
- 6 stat cards with trend indicators
- 3 chart types (line, donut, bar)
- Activity feed with date grouping
- Alerts banner with priority filtering
- Pull-to-refresh and auto-refresh
- Loading/error/empty states
- Responsive design for mobile/tablet/desktop
- Quick actions FAB
- 8 backend API endpoints integrated
- Unit and widget tests

---

**Maintained by**: SomniProperty Team
**Last Review**: December 2024
