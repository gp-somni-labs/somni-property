# Tenants Module - Architecture Diagrams

## Clean Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                            │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ UI (Pages/Widgets)                                              │ │
│  │  • TenantsListPage - List view with filters & search           │ │
│  │  • TenantDetailPage - Full tenant profile view                 │ │
│  │  • TenantFormPage - Create/Edit form with validation           │ │
│  │  • TenantCard - Reusable card component                        │ │
│  │  • TenantStatsCard - Statistics display widget                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                ↕                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ State Management (Riverpod)                                    │ │
│  │  • TenantsNotifier - List state & CRUD operations              │ │
│  │  • TenantDetailNotifier - Single tenant state                  │ │
│  │  • TenantsState - Immutable state container                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                ↕
┌─────────────────────────────────────────────────────────────────────┐
│                         Domain Layer                                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Entities (Business Objects)                                    │ │
│  │  • Tenant - Core tenant entity with computed properties        │ │
│  │  • EmergencyContact - Nested entity                            │ │
│  │  • TenantStatus - Type-safe enum                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                ↕                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Repository Interface (Abstract)                                │ │
│  │  • getTenants() → Either<Failure, List<Tenant>>                │ │
│  │  • getTenant(id) → Either<Failure, Tenant>                     │ │
│  │  • createTenant() → Either<Failure, Tenant>                    │ │
│  │  • updateTenant() → Either<Failure, Tenant>                    │ │
│  │  • deleteTenant() → Either<Failure, void>                      │ │
│  │  • searchTenants() → Either<Failure, List<Tenant>>             │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                ↕
┌─────────────────────────────────────────────────────────────────────┐
│                          Data Layer                                  │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Repository Implementation                                       │ │
│  │  • TenantRepositoryImpl - Implements domain interface          │ │
│  │  • Exception handling & error mapping                          │ │
│  │  • Model ↔ Entity conversion                                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                ↕                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Data Models (JSON Serialization)                               │ │
│  │  • TenantModel - Extends Tenant entity                         │ │
│  │  • fromJson() - Deserialize API response                       │ │
│  │  • toJson() - Serialize for API request                        │ │
│  │  • toCreateJson() - Special serialization for POST             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                ↕                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Remote Data Source (HTTP Client)                               │ │
│  │  • TenantRemoteDataSourceImpl                                  │ │
│  │  • Dio HTTP client integration                                 │ │
│  │  • API endpoint mapping                                        │ │
│  │  • Error handling & retry logic                                │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                ↕
┌─────────────────────────────────────────────────────────────────────┐
│                    External Dependencies                             │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ API Client (Shared)                                            │ │
│  │  • Dio configuration with interceptors                         │ │
│  │  • JWT token management                                        │ │
│  │  • Auto token refresh on 401                                   │ │
│  │  • Dynamic base URL (VPN/LAN/Public)                           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                ↕                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Backend API (NOT IMPLEMENTED)                                  │ │
│  │  ❌ FastAPI application missing                                 │ │
│  │  ❌ /api/v1/tenants endpoints not coded                         │ │
│  │  ❌ Database models not created                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow - List Tenants

```
┌──────────────┐
│ User opens   │
│ Tenants page │
└──────┬───────┘
       │
       ↓
┌──────────────────────┐
│ TenantsListPage      │
│ (UI Widget)          │
│ - initState()        │
│ - ref.watch()        │
└──────┬───────────────┘
       │ watches provider
       ↓
┌──────────────────────────────┐
│ tenantsProvider              │
│ (StateNotifierProvider)      │
│ - Auto calls loadTenants()   │
└──────┬───────────────────────┘
       │
       ↓
┌──────────────────────────────┐
│ TenantsNotifier.loadTenants()│
│ - Set isLoading = true       │
│ - Call repository            │
└──────┬───────────────────────┘
       │
       ↓
┌──────────────────────────────────────┐
│ TenantRepositoryImpl.getTenants()    │
│ - Call remote data source            │
│ - Handle exceptions                  │
│ - Convert models to entities         │
└──────┬───────────────────────────────┘
       │
       ↓
┌───────────────────────────────────────────┐
│ TenantRemoteDataSource.getTenants()       │
│ - GET /api/v1/tenants                     │
│ - Dio interceptor adds JWT token          │
│ - Parse JSON response                     │
└──────┬────────────────────────────────────┘
       │
       ↓
┌──────────────────────────┐
│ Backend API              │
│ ❌ NOT IMPLEMENTED        │
│ Would return:            │
│ [                        │
│   {                      │
│     "id": "uuid",        │
│     "first_name": "...", │
│     "last_name": "...",  │
│     ...                  │
│   }                      │
│ ]                        │
└──────┬───────────────────┘
       │ (currently fails)
       ↓
┌──────────────────────────────────┐
│ NetworkException thrown           │
│ "Unable to connect to server"    │
└──────┬───────────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ Repository catches exception     │
│ Returns Left(NetworkFailure)     │
└──────┬───────────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ Notifier updates state           │
│ - isLoading = false              │
│ - error = failure.message        │
│ - tenants = []                   │
└──────┬───────────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ UI rebuilds via ref.watch()      │
│ Shows error state with retry btn │
└──────────────────────────────────┘
```

## State Management Flow

```
┌────────────────────────────────────────────────────────────────┐
│                     Riverpod Provider Tree                      │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  networkInfoProvider                                            │
│         │                                                       │
│         ↓                                                       │
│  apiClientProvider ←── secureStorageProvider                   │
│         │                                                       │
│         ↓                                                       │
│  tenantRemoteDataSourceProvider                                │
│         │                                                       │
│         ↓                                                       │
│  tenantRepositoryProvider                                      │
│         │                                                       │
│         ├─────────────────────────────────┐                    │
│         ↓                                 ↓                    │
│  tenantsProvider                  tenantDetailProvider(id)     │
│  (StateNotifier)                  (Family StateNotifier)       │
│         │                                 │                    │
│         │                                 │                    │
│    ┌────┴─────┐                     ┌────┴─────┐              │
│    │ State:   │                     │ State:   │              │
│    │ ────────│                     │ ────────│              │
│    │ tenants │                     │ tenant  │              │
│    │ loading │                     │ loading │              │
│    │ error   │                     │ error   │              │
│    │ stats   │                     └──────────┘              │
│    └──────────┘                                               │
│         │                                                      │
│         │ watched by                                           │
│         ↓                                                      │
│  ┌──────────────────┐                                         │
│  │ TenantsListPage  │                                         │
│  │ (ConsumerWidget) │                                         │
│  └──────────────────┘                                         │
└────────────────────────────────────────────────────────────────┘
```

## CRUD Operations Flow

### CREATE Tenant

```
User fills form → Tap "Create" button
         ↓
TenantFormPage._submitForm()
         ↓
Create Tenant entity from form fields
         ↓
ref.read(tenantsProvider.notifier).createTenant(tenant)
         ↓
TenantsNotifier.createTenant()
  • Set isLoading = true
  • Call repository.createTenant()
         ↓
TenantRepositoryImpl.createTenant()
  • Convert entity to model
  • Call remoteDataSource.createTenant()
         ↓
TenantRemoteDataSource.createTenant()
  • POST /api/v1/tenants
  • Body: model.toCreateJson() (no ID)
         ↓
Backend creates tenant in DB, returns with ID
         ↓
Parse response → TenantModel
         ↓
Repository: Right(createdTenant.toEntity())
         ↓
Notifier: Add to tenants list
  • state = [...state.tenants, created]
  • isLoading = false
         ↓
Form: Pop navigation, show success snackbar
         ↓
List page: Automatically updates (watching provider)
```

### READ Tenant (Detail)

```
User taps tenant card in list
         ↓
context.push('/tenants/${tenant.id}')
         ↓
GoRouter navigates to TenantDetailPage(tenantId: id)
         ↓
TenantDetailPage.build()
  • ref.watch(tenantDetailProvider(id))
         ↓
tenantDetailProvider(id) auto-created
         ↓
TenantDetailNotifier.loadTenant() (in constructor)
  • Set isLoading = true
  • Call repository.getTenant(id)
         ↓
TenantRepositoryImpl.getTenant()
  • Call remoteDataSource.getTenant(id)
         ↓
TenantRemoteDataSource.getTenant()
  • GET /api/v1/tenants/{id}
         ↓
Backend fetches from DB by UUID
         ↓
Parse response → TenantModel
         ↓
Repository: Right(tenant.toEntity())
         ↓
Notifier: state = TenantDetailState(tenant: tenant)
         ↓
UI: Display tenant details
```

### UPDATE Tenant

```
User taps Edit button on detail page
         ↓
context.push('/tenants/${id}/edit')
         ↓
TenantFormPage(tenantId: id)
  • Load existing tenant data
  • Pre-populate form fields
         ↓
User modifies fields → Tap "Update"
         ↓
TenantFormPage._submitForm()
  • Create updated Tenant entity
         ↓
ref.read(tenantsProvider.notifier).updateTenant(tenant)
         ↓
TenantsNotifier.updateTenant()
  • Set isLoading = true
  • Call repository.updateTenant()
         ↓
TenantRepositoryImpl.updateTenant()
  • Convert entity to model
  • Call remoteDataSource.updateTenant()
         ↓
TenantRemoteDataSource.updateTenant()
  • PUT /api/v1/tenants/{id}
  • Body: model.toJson() (includes ID)
         ↓
Backend updates in DB, returns updated tenant
         ↓
Parse response → TenantModel
         ↓
Repository: Right(updated.toEntity())
         ↓
Notifier: Replace in list
  • state = tenants.map((t) => t.id == id ? updated : t)
  • isLoading = false
         ↓
Form: Pop navigation, show success snackbar
         ↓
List & detail pages: Auto-update (watching provider)
```

### DELETE Tenant

```
User taps Delete in overflow menu
         ↓
Show confirmation dialog
         ↓
User confirms → Tap "Delete"
         ↓
ref.read(tenantsProvider.notifier).deleteTenant(id)
         ↓
TenantsNotifier.deleteTenant()
  • Set isLoading = true
  • Call repository.deleteTenant(id)
         ↓
TenantRepositoryImpl.deleteTenant()
  • Call remoteDataSource.deleteTenant(id)
         ↓
TenantRemoteDataSource.deleteTenant()
  • DELETE /api/v1/tenants/{id}
         ↓
Backend soft-deletes or hard-deletes tenant
         ↓
Returns 204 No Content
         ↓
Repository: Right(null)
         ↓
Notifier: Remove from list
  • state = tenants.where((t) => t.id != id)
  • isLoading = false
         ↓
If on detail page: Pop navigation
If on list page: Show success snackbar
         ↓
List auto-updates (tenant removed)
```

## Error Handling Flow

```
┌──────────────────────┐
│ Any API Operation    │
└──────────┬───────────┘
           │
           ↓
    ┌──────────────┐
    │ Try API Call │
    └──────┬───────┘
           │
           ↓
    ┌──────────────────────────┐
    │ DioException thrown?     │
    └──┬───────────────────┬───┘
       │ NO                │ YES
       ↓                   ↓
┌─────────────┐     ┌──────────────────────┐
│ Success     │     │ Check exception type │
│ Parse JSON  │     └──────┬───────────────┘
└─────────────┘            │
                           ↓
                 ┌─────────────────────────┐
                 │ Connection Timeout?     │
                 │ → NetworkException      │
                 ├─────────────────────────┤
                 │ Connection Error?       │
                 │ → NetworkException      │
                 ├─────────────────────────┤
                 │ 401 Unauthorized?       │
                 │ → Try refresh token     │
                 │   ├─ Success: Retry     │
                 │   └─ Fail: AuthException│
                 ├─────────────────────────┤
                 │ 400 Bad Request?        │
                 │ → ValidationException   │
                 ├─────────────────────────┤
                 │ 404 Not Found?          │
                 │ → NotFoundException     │
                 ├─────────────────────────┤
                 │ 500 Server Error?       │
                 │ → ServerException       │
                 └─────────────────────────┘
                           │
                           ↓
                 ┌─────────────────────┐
                 │ Repository catches  │
                 │ Convert to Failure  │
                 └──────────┬──────────┘
                            │
                            ↓
                 ┌──────────────────────┐
                 │ Return Left(Failure) │
                 └──────────┬───────────┘
                            │
                            ↓
                 ┌──────────────────────┐
                 │ Notifier handles     │
                 │ - Set error message  │
                 │ - Set loading false  │
                 └──────────┬───────────┘
                            │
                            ↓
                 ┌──────────────────────┐
                 │ UI shows error state │
                 │ - Error icon         │
                 │ - Error message      │
                 │ - Retry button       │
                 └──────────────────────┘
```

## Authentication Flow

```
┌──────────────────────┐
│ User logs in         │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────────────┐
│ POST /api/v1/auth/login      │
│ Body: {email, password}      │
└──────────┬───────────────────┘
           │
           ↓
┌──────────────────────────────┐
│ Backend validates & returns: │
│ {                            │
│   access_token: "JWT...",    │
│   refresh_token: "JWT...",   │
│   user_id: "uuid",           │
│   role: "manager"            │
│ }                            │
└──────────┬───────────────────┘
           │
           ↓
┌────────────────────────────────┐
│ ApiClient.storeTokens()        │
│ - Save to FlutterSecureStorage │
│ - Save user_id & role          │
└──────────┬─────────────────────┘
           │
           ↓
┌────────────────────────────────┐
│ Navigate to /dashboard         │
└────────────────────────────────┘

        ... user browses app ...

┌────────────────────────────────┐
│ API request intercepted        │
│ (AuthInterceptor)              │
└──────────┬─────────────────────┘
           │
           ↓
┌────────────────────────────────┐
│ Get access token from storage  │
│ Add: Authorization: Bearer JWT │
└──────────┬─────────────────────┘
           │
           ↓
┌────────────────────────────────┐
│ Send request to API            │
└──────────┬─────────────────────┘
           │
           ↓
    ┌──────────────┐
    │ Response 401?│
    └──┬───────┬───┘
       │ NO    │ YES
       ↓       ↓
   ┌───────┐  ┌──────────────────────┐
   │Success│  │ Call refreshToken()  │
   └───────┘  └──────────┬───────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │ POST /api/v1/auth/   │
              │   refresh            │
              │ Body: {refresh_token}│
              └──────────┬───────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │ Returns new tokens?  │
              └──┬───────────────┬───┘
                 │ YES           │ NO
                 ↓               ↓
     ┌─────────────────┐  ┌──────────────┐
     │ Store new tokens│  │ Clear tokens │
     │ Retry request   │  │ Redirect to  │
     └─────────────────┘  │ /login       │
                          └──────────────┘
```

## Routing & Navigation

```
App Launch
    ↓
┌────────────────────┐
│ Check auth state   │
└────────┬───────────┘
         │
    ┌────┴─────┐
    │          │
    ↓          ↓
Authenticated  Not Authenticated
    │          │
    ↓          ↓
/dashboard    /login
    │
    │ User taps "Tenants" in nav
    ↓
┌────────────────────────┐
│ /tenants               │
│ (TenantsListPage)      │
│                        │
│ Actions:               │
│ ┌──────────────────┐   │
│ │ Tap "Add Tenant" │   │
│ └────────┬─────────┘   │
│          │             │
│          ↓             │
│    /tenants/new        │
│    (TenantFormPage)    │
│          │             │
│          │ Submit      │
│          ↓             │
│    context.pop()       │
│    Back to /tenants    │
│                        │
│ ┌──────────────────┐   │
│ │ Tap tenant card  │   │
│ └────────┬─────────┘   │
│          │             │
│          ↓             │
│    /tenants/{id}       │
│    (TenantDetailPage)  │
│          │             │
│    ┌─────┴─────┐       │
│    │           │       │
│    ↓           ↓       │
│  Tap Edit   Tap Delete │
│    │           │       │
│    ↓           │       │
│ /tenants/{id}  │       │
│   /edit        │       │
│ (TenantFormPage)       │
│    │           │       │
│    │ Submit    │ Confirm│
│    ↓           ↓       │
│  context.pop() │       │
│  Back to       │       │
│  /tenants/{id} │       │
│                ↓       │
│          context.pop() │
│          Back to       │
│          /tenants      │
└────────────────────────┘
```

## Component Hierarchy

```
MaterialApp
  └── ProviderScope (Riverpod)
      └── GoRouter
          └── AppShell (Navigation Rail/Bottom Nav)
              └── TenantsListPage
                  ├── AppBar
                  │   ├── Title: "Tenants"
                  │   └── IconButton (Refresh)
                  │
                  ├── Column
                  │   ├── Stats Cards (Horizontal List)
                  │   │   ├── TenantStatsCard (Total)
                  │   │   ├── TenantStatsCard (Active)
                  │   │   ├── TenantStatsCard (Pending)
                  │   │   └── TenantStatsCard (Inactive)
                  │   │
                  │   ├── Search & Filter Row
                  │   │   ├── TextField (Search)
                  │   │   └── PopupMenuButton (Status Filter)
                  │   │
                  │   └── Tenant List
                  │       └── RefreshIndicator
                  │           └── ListView.builder
                  │               └── TenantCard (repeated)
                  │                   ├── CircleAvatar
                  │                   ├── Column (Info)
                  │                   │   ├── Row (Name + Status)
                  │                   │   ├── Row (Email)
                  │                   │   └── Row (Phone + Lease)
                  │                   └── PopupMenuButton (Actions)
                  │
                  └── FloatingActionButton ("Add Tenant")
```

---

## Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                     Flutter Framework                        │
│                     Dart SDK 3.4+                            │
└─────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ↓                    ↓                    ↓
┌───────────────┐  ┌──────────────────┐  ┌──────────────┐
│ State Mgmt    │  │   Networking     │  │  Navigation  │
│ flutter_      │  │   dio            │  │  go_router   │
│ riverpod      │  │   connectivity_  │  │              │
│               │  │   plus           │  │              │
└───────────────┘  └──────────────────┘  └──────────────┘
        │                    │                    │
        ↓                    ↓                    ↓
┌───────────────┐  ┌──────────────────┐  ┌──────────────┐
│ Local Storage │  │   Security       │  │  UI/UX       │
│ sqflite       │  │   flutter_secure │  │  Material 3  │
│ shared_prefs  │  │   _storage       │  │  shimmer     │
│               │  │   flutter_appauth│  │  cached_     │
│               │  │                  │  │  network_    │
│               │  │                  │  │  image       │
└───────────────┘  └──────────────────┘  └──────────────┘
```

---

**Document Version:** 1.0
**Last Updated:** December 5, 2025
