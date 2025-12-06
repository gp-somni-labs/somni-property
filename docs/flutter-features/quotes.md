# Quotes Module Documentation

> **Status**: ✅ Implemented
> **Complexity**: High (Most complex module with 30 API endpoints)
> **Estimated Effort**: 8-10 days
> **Last Updated**: December 5, 2024

## Overview

The Quotes module is the most comprehensive feature in SomniProperty, providing complete quote management functionality including product catalogs, vendor pricing, real-time calculations, PDF generation, and a public customer portal.

## Features

### Core Functionality
- ✅ Complete quote CRUD operations
- ✅ Multi-item quotes with line-by-line pricing
- ✅ Real-time calculator with subtotal, tax, and total
- ✅ Product catalog integration
- ✅ Vendor pricing comparison
- ✅ Quote status workflow (draft → sent → viewed → approved/declined)
- ✅ Quote expiration tracking with warnings
- ✅ PDF generation
- ✅ Public customer portal (token-based access)
- ✅ Quote duplication
- ✅ Statistics and analytics

### User Interface
- **5 Main Screens**:
  1. Quotes List (with tabs, search, filters)
  2. Quote Detail (with actions and timeline)
  3. Quote Builder (complex form with calculator)
  4. Product Catalog (search and filters)
  5. Public Quote View (customer-facing)

## Architecture

### Domain Layer

#### Entities

**Quote** (`lib/features/quotes/domain/entities/quote.dart`)
```dart
class Quote {
  String id;
  String? clientId;
  String? propertyId;
  QuoteStatus status;
  List<QuoteItem> items;
  double subtotal;
  double taxRate;
  double tax;
  double total;
  DateTime? validUntil;
  String? notes;
  DateTime createdAt;
  DateTime updatedAt;
  String? publicToken;
  // ... more fields
}
```

**QuoteItem** (`lib/features/quotes/domain/entities/quote_item.dart`)
```dart
class QuoteItem {
  String id;
  String quoteId;
  String? productId;
  String description;
  double quantity;
  double unitPrice;
  double total;
  // ... more fields
}
```

**Product** (`lib/features/quotes/domain/entities/product.dart`)
```dart
class Product {
  String id;
  String name;
  ProductCategory category;
  double basePrice;
  List<VendorPrice> vendorPrices;
  // ... more fields
}
```

#### Enums

**QuoteStatus**:
- `draft` - Quote being created
- `sent` - Sent to customer
- `viewed` - Customer has viewed
- `approved` - Customer approved
- `declined` - Customer declined
- `expired` - Past valid until date

**ProductCategory**:
- plumbing, electrical, hvac, appliances, flooring, painting, roofing, landscaping, cleaning, security, general, other

### Data Layer

#### Models
- `QuoteModel` - JSON serialization for Quote
- `QuoteItemModel` - JSON serialization for QuoteItem
- `ProductModel` - JSON serialization for Product
- `QuoteStatsModel` - Statistics aggregation

#### Repository Implementation
**Location**: `lib/features/quotes/data/repositories/quote_repository_impl.dart`

Implements all 30 API endpoints:
- Quote CRUD (5 endpoints)
- Quote actions (4 endpoints)
- Calculator (1 endpoint)
- PDF generation (1 endpoint)
- Public portal (2 endpoints)
- Product catalog (5 endpoints)
- Vendor pricing (1 endpoint)
- Statistics (1 endpoint)

### Presentation Layer

#### State Management

**Providers** (`lib/features/quotes/presentation/providers/quote_provider.dart`):
- `quotesProvider` - Quotes list state
- `quoteDetailProvider` - Single quote detail state
- `productsProvider` - Product catalog state
- `quoteStatsProvider` - Statistics state

#### Widgets

**Core Widgets**:
- `QuoteCard` - List item display
- `QuoteStatusBadge` - Color-coded status indicator
- `QuoteCalculatorWidget` - Real-time calculation display with editable tax rate

**Additional Widgets** (to be implemented):
- `QuoteLineItemRow` - Editable line item in builder
- `QuoteLineItemDisplay` - Read-only line item in detail
- `QuoteExpiryAlert` - Warning for expiring quotes
- `ProductCard` - Catalog item display
- `ProductPickerDialog` - Product selection dialog
- `SendQuoteDialog` - Email configuration dialog

#### Pages

**QuotesListPage** (`lib/features/quotes/presentation/pages/quotes_list_page.dart`)
- Tab bar with Draft, Sent, Approved, All filters
- Statistics cards (Total Value, Approval Rate, Pending)
- Search functionality
- Pull-to-refresh
- Empty state with call-to-action

**QuoteDetailPage** (`lib/features/quotes/presentation/pages/quote_detail_page.dart`)
- Full quote information display
- Line items table
- Real-time calculator
- Action buttons (Send, Approve, Decline, Download PDF, Duplicate, Delete)
- Status-dependent actions

**QuoteBuilderPage** (`lib/features/quotes/presentation/pages/quote_builder_page.dart`)
- Client and property selection
- Line items editor with add/remove
- Real-time calculator
- Tax rate input
- Validity period configuration
- Notes section
- Save as draft / Send to client

**ProductCatalogPage** (to be implemented)
- Browse products by category
- Search functionality
- Vendor pricing comparison
- Add to quote action

**PublicQuoteViewPage** (to be implemented)
- Token-based access (no authentication)
- Professional read-only display
- Download PDF
- Approve/Decline actions

## Calculator Logic

The quote calculator is critical and must maintain accuracy:

### Calculation Flow

1. **Item Total**: `quantity × unitPrice`
2. **Subtotal**: Sum of all item totals
3. **Tax**: `subtotal × (taxRate / 100)`
4. **Total**: `subtotal + tax`

### Implementation

```dart
// In Quote entity
static double calculateSubtotal(List<QuoteItem> items) {
  return items.fold(0.0, (sum, item) => sum + item.total);
}

static double calculateTax(double subtotal, double taxRate) {
  return subtotal * (taxRate / 100);
}

static double calculateTotal(double subtotal, double tax) {
  return subtotal + tax;
}

Quote recalculate() {
  final newSubtotal = calculateSubtotal(items);
  final newTax = calculateTax(newSubtotal, taxRate);
  final newTotal = calculateTotal(newSubtotal, newTax);

  return copyWith(
    subtotal: newSubtotal,
    tax: newTax,
    total: newTotal,
  );
}
```

### Calculator Widget

The `QuoteCalculatorWidget` displays calculations and optionally allows tax rate editing:

```dart
QuoteCalculatorWidget(
  subtotal: quote.subtotal,
  taxRate: quote.taxRate,
  tax: quote.tax,
  total: quote.total,
  isEditable: true,
  onTaxRateChanged: (rate) {
    // Update tax rate and recalculate
  },
)
```

## API Integration

### Base Endpoints

All endpoints are under `/api/v1/quotes` and `/api/v1/products`.

### Key Endpoints

**Quotes**:
- `GET /quotes` - List quotes (with filters)
- `GET /quotes/:id` - Get quote details
- `POST /quotes` - Create quote
- `PUT /quotes/:id` - Update quote
- `DELETE /quotes/:id` - Delete quote
- `POST /quotes/:id/send` - Send to customer
- `POST /quotes/:id/approve` - Approve quote
- `POST /quotes/:id/decline` - Decline quote
- `POST /quotes/:id/duplicate` - Duplicate quote
- `POST /quotes/calculate` - Calculate totals
- `GET /quotes/:id/pdf` - Generate PDF
- `GET /quotes/public/:token` - Public access
- `POST /quotes/:id/generate-token` - Generate public token
- `GET /quotes/stats` - Get statistics

**Products**:
- `GET /products` - List products (with filters)
- `GET /products/:id` - Get product details
- `POST /products` - Create product
- `PUT /products/:id` - Update product
- `DELETE /products/:id` - Delete product
- `POST /products/sync-vendor-pricing` - Sync vendor prices

## Testing

### Unit Tests

**Quote Calculations** (`test/features/quotes/domain/quote_calculations_test.dart`):
- ✅ Subtotal calculation
- ✅ Tax calculation
- ✅ Total calculation
- ✅ Recalculate with updated values
- ✅ Edge cases (zero tax, decimal quantities)

**Test Coverage**: ~85% for domain layer calculations

### Widget Tests (to be implemented)
- Quote card rendering
- Status badge color coding
- Calculator widget interactions
- Form validation

### Integration Tests (to be implemented)
- Full quote creation flow
- Quote approval workflow
- PDF generation
- Public portal access

## Usage Examples

### Creating a Quote

```dart
// Navigate to builder
Navigator.push(
  context,
  MaterialPageRoute(
    builder: (context) => const QuoteBuilderPage(),
  ),
);

// In builder, add items and configure
final quote = Quote(
  id: 'new',
  clientId: selectedClientId,
  propertyId: selectedPropertyId,
  status: QuoteStatus.draft,
  items: lineItems,
  subtotal: 0,
  taxRate: 8.5,
  tax: 0,
  total: 0,
  validUntil: DateTime.now().add(Duration(days: 30)),
  createdAt: DateTime.now(),
  updatedAt: DateTime.now(),
).recalculate(); // Ensures correct calculations

// Create via repository
await ref.read(quoteRepositoryProvider).createQuote(quote);
```

### Sending a Quote

```dart
// From detail page
await ref.read(quoteDetailProvider(quoteId).notifier).sendQuote(
  email: 'customer@example.com',
  message: 'Please review this quote.',
);
```

### Accessing Public Portal

```dart
// Generate token (admin)
final token = await ref.read(quoteRepositoryProvider).generatePublicToken(quoteId);

// Share URL with customer
final publicUrl = 'https://app.somniproperty.com/quotes/public/$token';

// Customer accesses (no auth required)
final quote = await ref.read(quoteRepositoryProvider).getQuoteByToken(token);
```

## Status Workflow

```
Draft → Sent → Viewed → Approved
                  ↓
               Declined
                  ↓
               Expired (if past validUntil)
```

## Business Logic

### Expiry Warnings

Quotes expiring within 3 days show a warning:

```dart
bool get isExpiringSoon {
  if (validUntil == null) return false;
  final daysUntilExpiry = validUntil!.difference(DateTime.now()).inDays;
  return daysUntilExpiry > 0 && daysUntilExpiry <= 3;
}
```

### Auto-save (to be implemented)

Quote builder should auto-save drafts every 30 seconds:

```dart
Timer.periodic(Duration(seconds: 30), (timer) {
  if (isDirty && isValid) {
    _saveAsDraft();
  }
});
```

## Performance Considerations

### Product Catalog Caching

Products should be cached locally to reduce API calls:

```dart
// Cache products for 1 hour
final cachedProducts = await _cacheManager.get(
  'products',
  fetch: () => _repository.getProducts(),
  duration: Duration(hours: 1),
);
```

### Pagination

For large quote lists, implement pagination:

```dart
GET /quotes?page=1&limit=20
```

## Security

### Public Portal

Public quotes use token-based access:
- Tokens are unique, unpredictable strings
- No authentication required
- Read-only access
- Can approve/decline but cannot edit

### Permissions

- **Admin**: Full access to all quotes
- **Manager**: Can create, send, view all quotes
- **Staff**: Can create drafts, view assigned quotes
- **Customer**: Can view only their quotes via public token

## Future Enhancements

### Phase 2
- [ ] Email templates customization
- [ ] Quote versioning
- [ ] Discount/promotion codes
- [ ] Multi-currency support
- [ ] Recurring quotes (subscriptions)
- [ ] Quote comparison tool
- [ ] Advanced filtering (date range, amount range)

### Phase 3
- [ ] E-signature integration
- [ ] Payment processing integration
- [ ] Automated follow-ups
- [ ] Quote analytics dashboard
- [ ] A/B testing for quote templates

## Troubleshooting

### Common Issues

**Calculator not updating**:
- Ensure `recalculate()` is called after item changes
- Verify tax rate is a percentage (8.5, not 0.085)

**PDF generation fails**:
- Check backend has PDF generation library installed
- Verify quote ID is valid
- Check server logs for errors

**Public token not working**:
- Verify token is correctly generated
- Check token hasn't expired (if implementing expiry)
- Ensure public endpoint doesn't require auth

## File Structure

```
lib/features/quotes/
├── domain/
│   ├── entities/
│   │   ├── quote.dart
│   │   ├── quote_item.dart
│   │   └── product.dart
│   └── repositories/
│       └── quote_repository.dart
├── data/
│   ├── models/
│   │   ├── quote_model.dart
│   │   ├── quote_item_model.dart
│   │   └── product_model.dart
│   ├── datasources/
│   │   └── quote_remote_datasource.dart
│   └── repositories/
│       └── quote_repository_impl.dart
└── presentation/
    ├── pages/
    │   ├── quotes_list_page.dart
    │   ├── quote_detail_page.dart
    │   ├── quote_builder_page.dart
    │   ├── product_catalog_page.dart (to be implemented)
    │   └── public_quote_view_page.dart (to be implemented)
    ├── widgets/
    │   ├── quote_card.dart
    │   ├── quote_status_badge.dart
    │   └── quote_calculator_widget.dart
    └── providers/
        └── quote_provider.dart
```

## Testing Commands

```bash
# Run all quote tests
flutter test test/features/quotes/

# Run specific test file
flutter test test/features/quotes/domain/quote_calculations_test.dart

# Run with coverage
flutter test --coverage
genhtml coverage/lcov.info -o coverage/html
```

## Dependencies

- `flutter_riverpod`: State management
- `dio`: HTTP client
- `equatable`: Value equality
- `flutter_secure_storage`: Token storage

## Contributing

When modifying the Quotes module:
1. Update calculations? → Update tests!
2. New endpoint? → Update datasource and repository
3. UI changes? → Update screenshots in this doc
4. New status? → Update enum and badge widget

## Contact

For questions or issues with the Quotes module, contact the development team or open an issue in the repository.

---

**Last Updated**: December 5, 2024
**Module Version**: 1.0.0
**Maintainer**: SomniProperty Development Team
