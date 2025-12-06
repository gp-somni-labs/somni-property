import 'package:equatable/equatable.dart';
import 'quote_item.dart';

/// Quote entity representing a customer quote for services/products
class Quote extends Equatable {
  final String id;
  final String? clientId;
  final String? propertyId;
  final QuoteStatus status;
  final List<QuoteItem> items;
  final double subtotal;
  final double taxRate; // Percentage (e.g., 8.5 for 8.5%)
  final double tax;
  final double total;
  final DateTime? validUntil;
  final String? notes;
  final String? terms;
  final DateTime createdAt;
  final DateTime updatedAt;

  // Public portal access
  final String? publicToken;
  final DateTime? sentAt;
  final DateTime? viewedAt;
  final DateTime? approvedAt;
  final DateTime? declinedAt;

  // Joined data from related entities
  final String? clientName;
  final String? propertyAddress;
  final String? createdByName;

  const Quote({
    required this.id,
    this.clientId,
    this.propertyId,
    required this.status,
    required this.items,
    required this.subtotal,
    required this.taxRate,
    required this.tax,
    required this.total,
    this.validUntil,
    this.notes,
    this.terms,
    required this.createdAt,
    required this.updatedAt,
    this.publicToken,
    this.sentAt,
    this.viewedAt,
    this.approvedAt,
    this.declinedAt,
    this.clientName,
    this.propertyAddress,
    this.createdByName,
  });

  /// Check if quote is expired
  bool get isExpired {
    if (validUntil == null) return false;
    return DateTime.now().isAfter(validUntil!);
  }

  /// Check if quote is expiring soon (within 3 days)
  bool get isExpiringSoon {
    if (validUntil == null) return false;
    final daysUntilExpiry = validUntil!.difference(DateTime.now()).inDays;
    return daysUntilExpiry > 0 && daysUntilExpiry <= 3;
  }

  /// Get days until expiry (negative if expired)
  int? get daysUntilExpiry {
    if (validUntil == null) return null;
    return validUntil!.difference(DateTime.now()).inDays;
  }

  /// Check if quote has been sent
  bool get isSent => sentAt != null;

  /// Check if quote has been viewed by customer
  bool get isViewed => viewedAt != null;

  /// Get formatted subtotal
  String get formattedSubtotal => '\$${subtotal.toStringAsFixed(2)}';

  /// Get formatted tax
  String get formattedTax => '\$${tax.toStringAsFixed(2)}';

  /// Get formatted total
  String get formattedTotal => '\$${total.toStringAsFixed(2)}';

  /// Get formatted tax rate
  String get formattedTaxRate => '${taxRate.toStringAsFixed(2)}%';

  /// Get formatted valid until date
  String? get formattedValidUntil => validUntil != null
      ? '${validUntil!.month}/${validUntil!.day}/${validUntil!.year}'
      : null;

  /// Get item count
  int get itemCount => items.length;

  /// Calculate subtotal from items
  static double calculateSubtotal(List<QuoteItem> items) {
    return items.fold(0.0, (sum, item) => sum + item.total);
  }

  /// Calculate tax from subtotal and rate
  static double calculateTax(double subtotal, double taxRate) {
    return subtotal * (taxRate / 100);
  }

  /// Calculate total from subtotal and tax
  static double calculateTotal(double subtotal, double tax) {
    return subtotal + tax;
  }

  /// Recalculate all amounts based on items
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

  /// Copy with new values
  Quote copyWith({
    String? id,
    String? clientId,
    String? propertyId,
    QuoteStatus? status,
    List<QuoteItem>? items,
    double? subtotal,
    double? taxRate,
    double? tax,
    double? total,
    DateTime? validUntil,
    String? notes,
    String? terms,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? publicToken,
    DateTime? sentAt,
    DateTime? viewedAt,
    DateTime? approvedAt,
    DateTime? declinedAt,
    String? clientName,
    String? propertyAddress,
    String? createdByName,
  }) {
    return Quote(
      id: id ?? this.id,
      clientId: clientId ?? this.clientId,
      propertyId: propertyId ?? this.propertyId,
      status: status ?? this.status,
      items: items ?? this.items,
      subtotal: subtotal ?? this.subtotal,
      taxRate: taxRate ?? this.taxRate,
      tax: tax ?? this.tax,
      total: total ?? this.total,
      validUntil: validUntil ?? this.validUntil,
      notes: notes ?? this.notes,
      terms: terms ?? this.terms,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      publicToken: publicToken ?? this.publicToken,
      sentAt: sentAt ?? this.sentAt,
      viewedAt: viewedAt ?? this.viewedAt,
      approvedAt: approvedAt ?? this.approvedAt,
      declinedAt: declinedAt ?? this.declinedAt,
      clientName: clientName ?? this.clientName,
      propertyAddress: propertyAddress ?? this.propertyAddress,
      createdByName: createdByName ?? this.createdByName,
    );
  }

  @override
  List<Object?> get props => [
        id,
        clientId,
        propertyId,
        status,
        items,
        subtotal,
        taxRate,
        tax,
        total,
        validUntil,
        notes,
        terms,
        createdAt,
        updatedAt,
        publicToken,
        sentAt,
        viewedAt,
        approvedAt,
        declinedAt,
      ];
}

/// Quote status enumeration
enum QuoteStatus {
  draft,
  sent,
  viewed,
  approved,
  declined,
  expired;

  String get displayName {
    switch (this) {
      case QuoteStatus.draft:
        return 'Draft';
      case QuoteStatus.sent:
        return 'Sent';
      case QuoteStatus.viewed:
        return 'Viewed';
      case QuoteStatus.approved:
        return 'Approved';
      case QuoteStatus.declined:
        return 'Declined';
      case QuoteStatus.expired:
        return 'Expired';
    }
  }

  static QuoteStatus fromString(String value) {
    return QuoteStatus.values.firstWhere(
      (status) => status.name.toLowerCase() == value.toLowerCase(),
      orElse: () => QuoteStatus.draft,
    );
  }
}
