# Flutter Migration Gap Analysis

> **Date**: December 4, 2025
> **Vue Source**: `/tmp/somni-property-manager/frontend/` (195 files)
> **Flutter Target**: `/home/curiosity/.../somni-property/` (41 files)
> **Gap**: 154 files / ~79% features missing

---

## Executive Summary

| Metric | Vue | Flutter | Gap |
|--------|-----|---------|-----|
| **Total Files** | 195 | 41 | -154 |
| **Routes** | 60+ | 7 (4 placeholders) | -53 |
| **Data Models** | 36+ | 2 | -34 |
| **API Methods** | 150+ | ~10 | -140 |
| **Feature Categories** | 23 | 2 | -21 |

---

## Feature-by-Feature Gap Analysis

### Legend
- **Implemented** = Feature exists in Flutter
- **PLACEHOLDER** = Route exists but shows "coming soon"
- **MISSING** = Not implemented at all

---

## 1. Authentication & Authorization

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Login Page | `LoginView.vue` | `login_page.dart` | Implemented |
| OIDC/SSO Auth | Full Authelia | `oidc_datasource.dart` | Implemented |
| Token Refresh | api.ts interceptor | `api_client.dart` | Implemented |
| User Profile | Settings | - | MISSING |
| Role-based Access | Guards | - | MISSING |
| Session Management | - | - | MISSING |

---

## 2. Dashboard

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Main Dashboard | `Dashboard.vue` | `dashboard_page.dart` | Implemented (basic) |
| StatCards | `StatCard.vue` | - | MISSING |
| Quick Actions | `QuickActions.vue` | - | MISSING |
| Activity Feed | `ActivityFeed.vue` | - | MISSING |
| Occupancy Overview | `OccupancyOverview.vue` | - | MISSING |
| Dashboard Metrics | `useDashboardMetrics.ts` | - | MISSING |

---

## 3. Properties/Buildings/Units

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Properties List | `BuildingsView.vue` | `properties_list_page.dart` | Implemented |
| Property Detail | `BuildingDetailView.vue` | `property_detail_page.dart` | Implemented |
| Property Form | `BuildingFormView.vue` | `property_form_page.dart` | Implemented |
| Property Model | types/index.ts | `property_model.dart` | Implemented |
| Property Provider | stores/properties.ts | `property_provider.dart` | Implemented |
| **Buildings CRUD** | Full CRUD | - | MISSING |
| **Units List** | `UnitsView.vue` | - | MISSING |
| **Unit Detail** | `UnitDetailView.vue` | - | MISSING |
| **Floor Plans** | `FloorPlanAnnotator.vue` | - | MISSING |

---

## 4. Tenants

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Tenants List | `TenantsView.vue` | `TenantsPlaceholderPage` | PLACEHOLDER |
| Tenant Detail | `TenantDetailView.vue` | - | MISSING |
| Tenant Form | `TenantFormView.vue` | - | MISSING |
| Tenant Model | `Tenant` interface | - | MISSING |
| Tenant Store | `tenants.ts` | - | MISSING |
| Tenant Portal | `TenantDashboard.vue` | - | MISSING |
| AI Chat Modal | `AIChatModal.vue` | - | MISSING |
| Maintenance Request | `MaintenanceRequestModal.vue` | - | MISSING |

---

## 5. Leases

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Leases List | `LeasesView.vue` | `LeasesPlaceholderPage` | PLACEHOLDER |
| Lease Detail | `LeaseDetailView.vue` | - | MISSING |
| Lease Form | `LeaseFormView.vue` | - | MISSING |
| Lease Model | `Lease` interface | - | MISSING |
| Lease Store | `leases.ts` | - | MISSING |
| Lease Renewal | API method | - | MISSING |
| Lease Termination | API method | - | MISSING |
| Document Generation | API method | - | MISSING |

---

## 6. Payments

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Payments List | `PaymentsView.vue` | - | MISSING |
| Payment Detail | `PaymentDetailView.vue` | - | MISSING |
| Payment Form | `PaymentFormView.vue` | - | MISSING |
| Payment Model | `Payment` interface | - | MISSING |
| Payment Store | `payments.ts` | - | MISSING |
| Payment Processing | API methods | - | MISSING |
| Refund Processing | API method | - | MISSING |
| Financial Charts | `FinancialChart.vue` | - | MISSING |

---

## 7. Work Orders / Maintenance

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Work Orders List | `WorkOrdersView.vue` | `MaintenancePlaceholderPage` | PLACEHOLDER |
| Work Order Detail | `WorkOrderDetailView.vue` | - | MISSING |
| Work Order Form | `WorkOrderFormView.vue` | - | MISSING |
| Work Order Model | `WorkOrder` interface | - | MISSING |
| Work Order Store | `workorders.ts` | - | MISSING |
| Assignment Modal | `WorkOrderAssignModal.vue` | - | MISSING |
| Status Updates | `WorkOrderStatusModal.vue` | - | MISSING |
| Photo Management | `ComparisonPhotoManager.vue` | - | MISSING |
| Contractor Assignment | API method | - | MISSING |

---

## 8. Contractors

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Contractors List | `ContractorsView.vue` | - | MISSING |
| Contractor Detail | `ContractorDetailView.vue` | - | MISSING |
| Contractor Form | `ContractorFormView.vue` | - | MISSING |
| Contractor Model | `Contractor` interface | - | MISSING |
| Rating System | API methods | - | MISSING |
| Availability Calendar | - | - | MISSING |

---

## 9. Documents

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Documents List | `DocumentsView.vue` | - | MISSING |
| Document Detail | `DocumentDetailView.vue` | - | MISSING |
| Document Upload | API method | - | MISSING |
| Document Model | `Document` interface | - | MISSING |
| Document Store | `documents.ts` | - | MISSING |
| PDF Download | API method | - | MISSING |

---

## 10. Invoicing

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Invoices List | `InvoicesView.vue` | - | MISSING |
| Invoice Detail | `InvoiceDetailView.vue` | - | MISSING |
| Invoice Form | `InvoiceFormView.vue` | - | MISSING |
| Invoice Model | `Invoice` interface | - | MISSING |
| Invoice Store | `invoices.ts` | - | MISSING |
| PDF Generation | API method | - | MISSING |
| Email Delivery | API method | - | MISSING |
| InvoiceNinja Sync | API methods | - | MISSING |

---

## 11. Clients

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Clients List | `ClientsView.vue` | - | MISSING |
| Client Detail | `ClientDetailView.vue` | - | MISSING |
| Client Form | `ClientFormView.vue` | - | MISSING |
| Client Model | `Client` interface | - | MISSING |
| Client Store | `clients.ts` | - | MISSING |
| Onboarding Wizard | `ClientOnboardingView.vue` | - | MISSING |
| Media Management | `ClientMediaManagementView.vue` | - | MISSING |
| Infrastructure View | `ClientInfrastructureView.vue` | - | MISSING |

---

## 12. Quotes & Pricing

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Quotes List | `QuotesView.vue` | - | MISSING |
| Quote Detail | `QuoteDetailView.vue` | - | MISSING |
| Quote Form | `QuoteFormView.vue` | - | MISSING |
| Quote Calculator | `QuoteCalculator.vue` | - | MISSING |
| Quote Model | `Quote` interface | - | MISSING |
| Products Catalog | `ProductsView.vue` | - | MISSING |
| 3D Model Viewer | `Model3DViewer.vue` | - | MISSING |
| Pricing Comparison | `PricingTierComparison.vue` | - | MISSING |
| E-Signature | API method | - | MISSING |
| Public Quote Portal | `PublicQuoteView.vue` | - | MISSING |

---

## 13. Smart Home / IoT

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Smart Devices List | `SmartDevicesView.vue` | - | MISSING |
| Device Detail | `SmartDeviceDetailView.vue` | - | MISSING |
| Device Control | `DeviceControlCard.vue` | - | MISSING |
| Device Model | `SmartDevice` interface | - | MISSING |
| Device Store | `smartDevices.ts` | - | MISSING |
| Thermostat Control | `ThermostatCard.vue` | - | MISSING |
| Light Control | `LightCard.vue` | - | MISSING |
| Lock Control | `LockCard.vue` | - | MISSING |
| Camera Preview | `CameraCard.vue` | - | MISSING |
| Edge Nodes | `PropertyEdgeNode` | - | MISSING |
| Automations | `AutomationsView.vue` | - | MISSING |

---

## 14. Service Packages & Contracts

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Packages List | `ServicePackagesView.vue` | - | MISSING |
| Package Detail | `ServicePackageDetailView.vue` | - | MISSING |
| Contracts List | `ServiceContractsView.vue` | - | MISSING |
| Contract Detail | `ServiceContractDetailView.vue` | - | MISSING |
| Package Model | `ServicePackage` interface | - | MISSING |
| Contract Model | `ServiceContract` interface | - | MISSING |
| Package Store | `servicePackages.ts` | - | MISSING |
| Contract Store | `serviceContracts.ts` | - | MISSING |

---

## 15. Hub-Spoke Federation

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Hubs List | `HubsView.vue` | - | MISSING |
| Hub Detail | `HubDetailView.vue` | - | MISSING |
| Component Browser | `ComponentBrowser.vue` | - | MISSING |
| Fleet Management | `FleetManagement.vue` | - | MISSING |
| System Health | `SystemHealth.vue` | - | MISSING |
| Component Sync | `componentSync.ts` | - | MISSING |
| Service Catalog | `serviceCatalog.ts` | - | MISSING |
| GitOps Sync | API methods | - | MISSING |

---

## 16. Analytics & Reporting

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Analytics Dashboard | `AnalyticsView.vue` | - | MISSING |
| Financial Reports | Charts | - | MISSING |
| Occupancy Reports | `OccupancyChart.vue` | - | MISSING |
| Usage Charts | `UsageChart.vue` | - | MISSING |
| Portfolio Metrics | `usePortfolio.ts` | - | MISSING |
| Report Export | PDF/CSV | - | MISSING |

---

## 17. Alerts & Support

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Alerts List | `AlertsView.vue` | - | MISSING |
| Alert Detail | `AlertDetailView.vue` | - | MISSING |
| Alert Model | `Alert` interface | - | MISSING |
| Alert Composable | `useAlerts.ts` | - | MISSING |
| Support Tickets | `SupportTicketsView.vue` | - | MISSING |
| Ticket Detail | `SupportTicketDetailView.vue` | - | MISSING |
| Ticket Model | `SupportTicket` interface | - | MISSING |

---

## 18. Scheduling & Calendar

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Scheduling View | `SchedulingView.vue` | - | MISSING |
| Cal.com Integration | `CalComIntegration.vue` | - | MISSING |
| Rally Integration | `RallyIntegration.vue` | - | MISSING |
| Appointment Booking | - | - | MISSING |

---

## 19. AI Assistant

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| AI Chat Interface | `AIAssistant.vue` | - | MISSING |
| AI Context Awareness | API methods | - | MISSING |
| Tenant AI Chat | `AIChatModal.vue` | - | MISSING |

---

## 20. Customer Portal

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Progress View | `CustomerProgressView.vue` | - | MISSING |
| Payment Portal | `CustomerPaymentView.vue` | - | MISSING |
| Quote View | `CustomerQuoteView.vue` | - | MISSING |
| Public Quote | `PublicQuoteView.vue` | - | MISSING |

---

## 21. Settings

| Feature | Vue | Flutter | Status |
|---------|-----|---------|--------|
| Settings Overview | `SettingsView.vue` | `SettingsPlaceholderPage` | PLACEHOLDER |
| Preferences | `PreferencesView.vue` | - | MISSING |
| Integrations | `IntegrationsView.vue` | - | MISSING |
| Security | `SecurityView.vue` | - | MISSING |
| Labor Config | `LaborConfigSettings.vue` | - | MISSING |
| Theme Switching | `useTheme.ts` | - | MISSING |
| Cluster Management | `ClusterManagement.vue` | - | MISSING |

---

## Priority Implementation Order

### Phase 1: Core Features (Critical)
1. **Tenants** - Full CRUD + tenant model
2. **Leases** - Full CRUD + lease model
3. **Payments** - Full CRUD + payment processing
4. **Work Orders** - Full CRUD + assignment

### Phase 2: Business Features (High)
5. **Clients** - Full CRUD + onboarding
6. **Quotes** - Quote builder + calculator
7. **Invoicing** - Invoice generation
8. **Contractors** - CRUD + ratings

### Phase 3: Smart Home (Medium)
9. **Smart Devices** - Device inventory + control
10. **Edge Nodes** - Node management
11. **Automations** - Rule builder

### Phase 4: Advanced Features (Lower)
12. **Hub-Spoke Federation** - Component sync
13. **Analytics** - Charts + reports
14. **Alerts** - Alert system
15. **Customer Portal** - Public pages

---

## Data Models to Create

### Core Models (Priority 1)
```dart
// lib/features/tenants/domain/entities/tenant.dart
// lib/features/leases/domain/entities/lease.dart
// lib/features/payments/domain/entities/payment.dart
// lib/features/work_orders/domain/entities/work_order.dart
```

### Business Models (Priority 2)
```dart
// lib/features/clients/domain/entities/client.dart
// lib/features/quotes/domain/entities/quote.dart
// lib/features/invoices/domain/entities/invoice.dart
// lib/features/contractors/domain/entities/contractor.dart
// lib/features/documents/domain/entities/document.dart
```

### Smart Home Models (Priority 3)
```dart
// lib/features/smart_devices/domain/entities/smart_device.dart
// lib/features/edge_nodes/domain/entities/edge_node.dart
// lib/features/service_packages/domain/entities/service_package.dart
// lib/features/service_contracts/domain/entities/service_contract.dart
```

### Support Models (Priority 4)
```dart
// lib/features/alerts/domain/entities/alert.dart
// lib/features/support_tickets/domain/entities/support_ticket.dart
```

---

## API Service Methods to Implement

### Current State (api_client.dart)
- Basic Dio client with auth interceptors
- Token refresh mechanism
- VPN/local URL switching

### Needed Additions
1. Add all CRUD methods for each feature
2. Add request caching (like Vue's `cachedGet`)
3. Add request deduplication
4. Add WebSocket support for real-time updates

---

## Estimated Effort

| Category | Files Needed | Estimated Days |
|----------|--------------|----------------|
| Tenants Feature | 10 | 2 |
| Leases Feature | 10 | 2 |
| Payments Feature | 12 | 3 |
| Work Orders Feature | 15 | 3 |
| Clients Feature | 15 | 3 |
| Quotes Feature | 20 | 4 |
| Invoicing Feature | 12 | 2 |
| Contractors Feature | 10 | 2 |
| Documents Feature | 10 | 2 |
| Smart Devices Feature | 18 | 4 |
| Service Packages | 10 | 2 |
| Hub-Spoke Federation | 15 | 3 |
| Analytics | 10 | 2 |
| Alerts & Support | 12 | 2 |
| Customer Portal | 8 | 2 |
| Settings | 8 | 1 |
| **TOTAL** | **185** | **~39 days** |

---

## Next Steps

1. Start with Phase 1: Tenants feature
2. Create clean architecture structure (data/domain/presentation)
3. Implement models, repositories, providers
4. Create list/detail/form pages
5. Connect to backend API
6. Test and iterate

---

*Generated: December 4, 2025*
