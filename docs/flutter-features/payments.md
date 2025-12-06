# Payments Module Documentation

> **Module**: Payments
> **Status**: Complete with Stripe Integration
> **Last Updated**: December 2025
> **Coverage**: Domain, Data, Presentation layers

## Overview

The Payments module provides comprehensive payment management functionality for the SomniProperty platform, including Stripe credit card payment processing, manual payment recording, late fee management, and financial reporting.

## Architecture

The module follows Clean Architecture principles with three layers:

### Domain Layer (`lib/features/payments/domain/`)

#### Entities
- **Payment**: Core payment entity with:
  - Basic fields: ID, amount, dates, status, type, method
  - Stripe integration: `stripePaymentIntentId`, `last4`, `receiptUrl`, `failureReason`
  - Calculated fields: `isOverdue`, `daysOverdue`, `totalAmount`, `hasLateFee`
  - Related data: `tenantName`, `unitNumber`, `leaseId`

#### Enums
- **PaymentStatus**: pending, paid, partial, overdue, cancelled, refunded
- **PaymentType**: rent, deposit, lateFee, utility, maintenance, other
- **PaymentMethod**: cash, check, creditCard, debitCard, bankTransfer, online, other

#### Repositories
- **PaymentRepository**: Abstract interface defining all payment operations
  - CRUD operations
  - Stripe payment processing
  - Receipt generation
  - Late fee management
  - Payment statistics

### Data Layer (`lib/features/payments/data/`)

#### Data Sources
- **PaymentRemoteDataSource**: API client for backend communication
  - REST API endpoints at `/api/v1/payments`
  - Stripe endpoints: `/stripe/create-intent`, `/stripe/confirm`, `/stripe/refund`
  - Receipt endpoint: `/{id}/receipt`

#### Services
- **StripeService**: Stripe payment processing service
  - Initialize Stripe SDK with publishable key
  - Create payment intents on backend
  - Present Stripe payment sheet
  - Confirm payments on backend
  - Handle 3D Secure authentication
  - Process refunds

#### Models
- **PaymentModel**: JSON serialization for API communication
- **PaymentStatsModel**: Aggregated payment statistics

#### Repository Implementation
- **PaymentRepositoryImpl**: Implements PaymentRepository with error handling
  - Converts Dio exceptions to Failures
  - Maps between models and entities

### Presentation Layer (`lib/features/payments/presentation/`)

#### Pages
1. **PaymentsListPage**: Main list view with filtering and stats
   - Tab-based filtering (Pending, Overdue, Paid, All)
   - Payment statistics cards
   - Quick actions (Record, Apply Late Fee)
   - Pull-to-refresh

2. **PaymentDetailPage**: Detailed payment view
   - Status header with visual indicator
   - Amount details with late fees
   - Payment information (type, dates, method)
   - Associated records (tenant, unit, lease)
   - Quick actions (Record, Refund, Cancel, Delete)
   - Stripe transaction details

3. **PaymentFormPage**: Create/edit payment form
   - Payment type selection
   - Associated record pickers (lease, tenant, unit)
   - Amount and late fee inputs
   - Date pickers (due date, paid date)
   - Status and method dropdowns
   - Transaction ID input
   - Notes field

4. **PaymentStripePage**: Stripe payment processor
   - Loads payment details
   - Initiates Stripe payment flow
   - Displays success/error messages
   - Refreshes payment data on completion

#### Widgets
1. **PaymentCard**: List item displaying payment summary
   - Type icon and status badge
   - Tenant name and unit number
   - Amount and due date
   - Late fee indicator
   - Overdue warning
   - Quick action buttons

2. **PaymentStatsCard**: Statistics display card
   - Icon with colored background
   - Large value display
   - Description label

3. **PaymentMethodIcon**: Icon for payment method
   - Cash, check, credit card, bank transfer icons
   - Customizable size and color

4. **OverduePaymentAlert**: Banner for overdue payments
   - Overdue count and total amount
   - Tap to view overdue payments
   - Red warning theme

5. **StripePaymentDialog**: Stripe payment processing dialog
   - Payment summary display
   - Security notice
   - Error message display
   - Pay Now button with loading state

#### Providers (Riverpod)
- **paymentsProvider**: List state management
- **paymentDetailProvider**: Single payment detail
- **PaymentsNotifier**: State management methods:
  - `loadPayments()`: Load all with filters
  - `filterByStatus()`: Filter by payment status
  - `loadOverduePayments()`: Load overdue only
  - `loadUpcomingPayments()`: Load upcoming payments
  - `createPayment()`, `updatePayment()`: CRUD operations
  - `recordPayment()`: Mark payment as paid
  - `applyLateFee()`: Add late fee
  - `cancelPayment()`, `refundPayment()`: Cancel/refund
  - `deletePayment()`: Delete payment

## Stripe Integration

### Setup

1. **Add Stripe Publishable Key**:
```dart
// In app initialization
await StripeService.initialize('pk_test_...');
```

2. **Configure Backend**:
   - Backend must have Stripe secret key configured
   - Endpoints must be implemented:
     - `POST /api/v1/payments/{id}/stripe/create-intent`
     - `POST /api/v1/payments/{id}/stripe/confirm`
     - `POST /api/v1/payments/{id}/stripe/refund`

### Payment Flow

1. **Create Payment Intent** (Backend):
   - Client requests payment intent creation
   - Backend creates Stripe PaymentIntent
   - Backend returns `client_secret` and `payment_intent_id`

2. **Present Payment Sheet** (Frontend):
   - Initialize Stripe payment sheet with client secret
   - Present sheet to user
   - User enters card details
   - Stripe handles 3D Secure if needed
   - Stripe confirms payment

3. **Confirm on Backend**:
   - Frontend notifies backend of successful payment
   - Backend verifies payment with Stripe
   - Backend updates payment record with:
     - Status: paid
     - Stripe payment intent ID
     - Card last 4 digits
     - Receipt URL
   - Backend returns updated payment

### Error Handling

- **Card Declined**: Display error message from Stripe
- **Insufficient Funds**: Show user-friendly error
- **3D Secure Required**: Automatically handled by Stripe
- **Network Error**: Retry or show offline message
- **Backend Error**: Log and display generic error

### Security

- **Never store full card numbers** - Only last 4 digits
- **Use Stripe tokens** - Card data never touches backend
- **Server-side validation** - All amounts validated on backend
- **Secure receipts** - Receipt URLs should be signed/temporary
- **Audit logging** - Log all payment actions

## Financial Calculations

### Total Amount
```dart
double get totalAmount => amount + (lateFee ?? 0);
```

### Days Overdue
```dart
int get daysOverdue => DateTime.now().difference(dueDate).inDays;
```

### Overdue Status
```dart
bool get isOverdue =>
  status == PaymentStatus.pending &&
  DateTime.now().isAfter(dueDate);
```

### Payment Statistics
- **Total Paid**: Sum of all paid payment amounts
- **Total Overdue**: Sum of all overdue payment amounts
- **Collection Rate**: (Paid / (Paid + Due)) * 100
- **Pending Count**: Count of pending payments

## API Endpoints

### Base: `/api/v1/payments`

#### List Payments
```
GET /api/v1/payments
Query Parameters:
  - lease_id: string (optional)
  - tenant_id: string (optional)
  - unit_id: string (optional)
  - status: string (optional) - pending, paid, overdue, etc.
  - type: string (optional) - rent, deposit, etc.
  - from_date: ISO8601 datetime (optional)
  - to_date: ISO8601 datetime (optional)

Response: List of payment objects
```

#### Get Payment Detail
```
GET /api/v1/payments/{id}

Response: Payment object with joined data
```

#### Create Payment
```
POST /api/v1/payments
Body: {
  "lease_id": "string",
  "tenant_id": "string",
  "unit_id": "string",
  "amount": number,
  "due_date": "ISO8601",
  "status": "string",
  "type": "string",
  "notes": "string" (optional)
}

Response: Created payment object
```

#### Record Payment
```
POST /api/v1/payments/{id}/record
Body: {
  "paid_date": "ISO8601",
  "method": "string",
  "transaction_id": "string" (optional)
}

Response: Updated payment object
```

#### Apply Late Fee
```
POST /api/v1/payments/{id}/late-fee
Body: {
  "amount": number
}

Response: Updated payment object with late fee
```

#### Cancel Payment
```
POST /api/v1/payments/{id}/cancel
Body: {
  "reason": "string"
}

Response: Cancelled payment object
```

#### Refund Payment
```
POST /api/v1/payments/{id}/refund
Body: {
  "reason": "string"
}

Response: Refunded payment object
```

#### Get Overdue Payments
```
GET /api/v1/payments/overdue

Response: List of overdue payments
```

#### Get Upcoming Payments
```
GET /api/v1/payments/upcoming?within_days=7

Response: List of payments due within specified days
```

#### Get Payment Statistics
```
GET /api/v1/payments/stats
Query Parameters:
  - from_date: ISO8601 (optional)
  - to_date: ISO8601 (optional)

Response: {
  "total_payments": number,
  "pending_payments": number,
  "paid_payments": number,
  "overdue_payments": number,
  "total_amount_due": number,
  "total_amount_paid": number,
  "total_overdue": number,
  "collection_rate": number
}
```

#### Get Payment Receipt
```
GET /api/v1/payments/{id}/receipt

Response: {
  "receipt_url": "string"
}
```

#### Stripe - Create Payment Intent
```
POST /api/v1/payments/{id}/stripe/create-intent
Body: {
  "amount": number (cents),
  "currency": "string" (default: "usd"),
  "customer_id": "string" (optional),
  "metadata": object (optional)
}

Response: {
  "client_secret": "string",
  "payment_intent_id": "string",
  "ephemeral_key": "string" (optional),
  "customer_id": "string" (optional)
}
```

#### Stripe - Confirm Payment
```
POST /api/v1/payments/{id}/stripe/confirm
Body: {
  "payment_intent_id": "string"
}

Response: Updated payment object with Stripe details
```

#### Stripe - Refund
```
POST /api/v1/payments/{id}/stripe/refund
Body: {
  "amount": number (cents, optional - full refund if not specified),
  "reason": "string" (optional)
}

Response: Refunded payment object
```

## Offline Support

### Cached Data
- Payment list (read-only cache)
- Payment details (read-only cache)
- Payment statistics (read-only cache)

### Offline Queue
- **Cash payments**: Queue for sync when online
- **Check payments**: Queue for sync when online
- **Card payments**: **REQUIRE online connection** (cannot queue)

### Offline Indicators
- Show offline banner when network unavailable
- Disable Stripe payment option when offline
- Show sync status for queued payments
- Auto-sync when connection restored

## Testing

### Unit Tests (`test/features/payments/domain/entities/payment_test.dart`)
- Payment calculations (totalAmount, daysOverdue)
- Overdue detection
- Date formatting
- Enum conversions
- Copy with functionality
- Stripe field handling

### Widget Tests
- PaymentCard rendering
- PaymentStatsCard display
- Form validation
- Button interactions
- Status badge colors

### Integration Tests
- Full payment creation flow
- Stripe payment processing (test mode)
- Receipt generation
- Late fee application
- Refund processing

### Test Coverage Target
**80%+ coverage** across all layers

## Common Use Cases

### 1. Record Cash Payment
```dart
final success = await ref.read(paymentsProvider.notifier).recordPayment(
  paymentId,
  DateTime.now(),
  PaymentMethod.cash,
  null, // no transaction ID
);
```

### 2. Process Stripe Card Payment
```dart
final apiClient = ref.read(apiClientProvider);
final stripeService = StripeService(apiClient);

final success = await showStripePaymentDialog(
  context: context,
  payment: payment,
  stripeService: stripeService,
);
```

### 3. Apply Late Fee
```dart
final success = await ref.read(paymentsProvider.notifier).applyLateFee(
  paymentId,
  50.00, // late fee amount
);
```

### 4. Get Overdue Payments
```dart
await ref.read(paymentsProvider.notifier).loadOverduePayments();
final overduePayments = ref.read(paymentsProvider).payments;
```

### 5. Filter by Status
```dart
await ref.read(paymentsProvider.notifier).filterByStatus(
  PaymentStatus.paid,
);
```

### 6. Generate Monthly Rent Payments
```dart
final result = await ref.read(paymentRepositoryProvider).generateMonthlyPayments(
  12, // December
  2025,
);
```

## Security Considerations

### PCI Compliance
- **No card data storage**: Card numbers never stored
- **Stripe tokenization**: Use Stripe tokens only
- **TLS encryption**: All API calls over HTTPS
- **Secure display**: Only show last 4 digits

### Financial Validation
- **Server-side validation**: All amounts validated on backend
- **Double-check totals**: Verify calculated amounts
- **Audit trail**: Log all payment modifications
- **Idempotency**: Prevent duplicate payments

### Access Control
- **Authentication required**: All payment endpoints require auth
- **Authorization**: Users can only access their own payments
- **Admin permissions**: Certain actions require admin role
- **Audit logging**: Track who made changes

## Troubleshooting

### Stripe Payment Fails

**Card Declined**:
- Error message displayed to user
- Check with card issuer

**Network Error**:
- Retry payment
- Check internet connection
- Verify backend is accessible

**Backend Error**:
- Check backend logs
- Verify Stripe API key configured
- Check webhook configuration

### Payment Not Syncing

**Offline Queue Issue**:
- Check network connection
- Verify backend accessible
- Check local storage permissions

**Data Inconsistency**:
- Force refresh payment list
- Clear cache and reload
- Check backend data

### Receipt Not Generating

**URL Not Found**:
- Verify backend receipt generation
- Check PDF generation service
- Verify receipt URL is valid

## Future Enhancements

1. **Recurring Payments**: Auto-charge saved payment methods
2. **Payment Plans**: Split payments into installments
3. **ACH Bank Transfers**: Direct bank account payments
4. **Payment Reminders**: Automated email/SMS reminders
5. **Partial Payments**: Accept partial payment amounts
6. **Multi-Currency**: Support multiple currencies
7. **Payment Analytics**: Advanced financial reporting
8. **Saved Payment Methods**: Store cards for future use
9. **Autopay**: Automatic payment on due date
10. **Payment History Export**: CSV/Excel export

## Files Reference

### Domain Layer
- `lib/features/payments/domain/entities/payment.dart`
- `lib/features/payments/domain/repositories/payment_repository.dart`

### Data Layer
- `lib/features/payments/data/models/payment_model.dart`
- `lib/features/payments/data/datasources/payment_remote_datasource.dart`
- `lib/features/payments/data/repositories/payment_repository_impl.dart`
- `lib/features/payments/data/services/stripe_service.dart`

### Presentation Layer
- `lib/features/payments/presentation/pages/payments_list_page.dart`
- `lib/features/payments/presentation/pages/payment_detail_page.dart`
- `lib/features/payments/presentation/pages/payment_form_page.dart`
- `lib/features/payments/presentation/pages/payment_stripe_page.dart`
- `lib/features/payments/presentation/providers/payment_provider.dart`
- `lib/features/payments/presentation/widgets/payment_card.dart`
- `lib/features/payments/presentation/widgets/payment_stats_card.dart`
- `lib/features/payments/presentation/widgets/payment_method_icon.dart`
- `lib/features/payments/presentation/widgets/overdue_payment_alert.dart`
- `lib/features/payments/presentation/widgets/stripe_payment_dialog.dart`

### Tests
- `test/features/payments/domain/entities/payment_test.dart`

## Dependencies

```yaml
dependencies:
  flutter_stripe: ^11.3.0  # Stripe SDK for Flutter
  dartz: ^0.10.1           # Functional programming (Either)
  equatable: ^2.0.5        # Value equality
  flutter_riverpod: ^2.4.9 # State management
  dio: ^5.4.0              # HTTP client
  intl: ^0.18.1            # Date formatting
```

## Support

For questions or issues with the Payments module:
- Check this documentation first
- Review test files for usage examples
- Check backend API documentation
- Review Stripe integration guide
- Contact development team

---

**Document Version**: 1.0
**Last Review**: December 2025
**Next Review**: March 2026
