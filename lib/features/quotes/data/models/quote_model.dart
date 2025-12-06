import 'package:somni_property/features/quotes/domain/entities/quote.dart';
import 'package:somni_property/features/quotes/domain/entities/quote_item.dart';
import 'quote_item_model.dart';

/// Quote model for JSON serialization
class QuoteModel extends Quote {
  const QuoteModel({
    required super.id,
    super.clientId,
    super.propertyId,
    required super.status,
    required super.items,
    required super.subtotal,
    required super.taxRate,
    required super.tax,
    required super.total,
    super.validUntil,
    super.notes,
    super.terms,
    required super.createdAt,
    required super.updatedAt,
    super.publicToken,
    super.sentAt,
    super.viewedAt,
    super.approvedAt,
    super.declinedAt,
    super.clientName,
    super.propertyAddress,
    super.createdByName,
  });

  /// Create model from JSON
  factory QuoteModel.fromJson(Map<String, dynamic> json) {
    // Parse items
    List<QuoteItem> items = [];
    if (json['items'] != null) {
      items = (json['items'] as List)
          .map((item) => QuoteItemModel.fromJson(item))
          .toList();
    }

    return QuoteModel(
      id: json['id']?.toString() ?? '',
      clientId: json['client_id']?.toString() ?? json['clientId']?.toString(),
      propertyId: json['property_id']?.toString() ?? json['propertyId']?.toString(),
      status: QuoteStatus.fromString(
        json['status']?.toString() ?? 'draft',
      ),
      items: items,
      subtotal: (json['subtotal'] as num?)?.toDouble() ?? 0.0,
      taxRate: (json['tax_rate'] as num?)?.toDouble() ??
               (json['taxRate'] as num?)?.toDouble() ?? 0.0,
      tax: (json['tax'] as num?)?.toDouble() ?? 0.0,
      total: (json['total'] as num?)?.toDouble() ?? 0.0,
      validUntil: json['valid_until'] != null
          ? DateTime.parse(json['valid_until'])
          : json['validUntil'] != null
              ? DateTime.parse(json['validUntil'])
              : null,
      notes: json['notes']?.toString(),
      terms: json['terms']?.toString(),
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : json['createdAt'] != null
              ? DateTime.parse(json['createdAt'])
              : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : json['updatedAt'] != null
              ? DateTime.parse(json['updatedAt'])
              : DateTime.now(),
      publicToken: json['public_token']?.toString() ?? json['publicToken']?.toString(),
      sentAt: json['sent_at'] != null
          ? DateTime.parse(json['sent_at'])
          : json['sentAt'] != null
              ? DateTime.parse(json['sentAt'])
              : null,
      viewedAt: json['viewed_at'] != null
          ? DateTime.parse(json['viewed_at'])
          : json['viewedAt'] != null
              ? DateTime.parse(json['viewedAt'])
              : null,
      approvedAt: json['approved_at'] != null
          ? DateTime.parse(json['approved_at'])
          : json['approvedAt'] != null
              ? DateTime.parse(json['approvedAt'])
              : null,
      declinedAt: json['declined_at'] != null
          ? DateTime.parse(json['declined_at'])
          : json['declinedAt'] != null
              ? DateTime.parse(json['declinedAt'])
              : null,
      clientName: json['client_name']?.toString() ?? json['clientName']?.toString(),
      propertyAddress: json['property_address']?.toString() ??
                      json['propertyAddress']?.toString(),
      createdByName: json['created_by_name']?.toString() ??
                    json['createdByName']?.toString(),
    );
  }

  /// Convert model to JSON for API requests
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      if (clientId != null) 'client_id': clientId,
      if (propertyId != null) 'property_id': propertyId,
      'status': status.name,
      'items': items.map((item) => QuoteItemModel.fromEntity(item).toJson()).toList(),
      'subtotal': subtotal,
      'tax_rate': taxRate,
      'tax': tax,
      'total': total,
      if (validUntil != null) 'valid_until': validUntil!.toIso8601String(),
      if (notes != null) 'notes': notes,
      if (terms != null) 'terms': terms,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      if (publicToken != null) 'public_token': publicToken,
      if (sentAt != null) 'sent_at': sentAt!.toIso8601String(),
      if (viewedAt != null) 'viewed_at': viewedAt!.toIso8601String(),
      if (approvedAt != null) 'approved_at': approvedAt!.toIso8601String(),
      if (declinedAt != null) 'declined_at': declinedAt!.toIso8601String(),
    };
  }

  /// Create model from entity
  factory QuoteModel.fromEntity(Quote quote) {
    return QuoteModel(
      id: quote.id,
      clientId: quote.clientId,
      propertyId: quote.propertyId,
      status: quote.status,
      items: quote.items,
      subtotal: quote.subtotal,
      taxRate: quote.taxRate,
      tax: quote.tax,
      total: quote.total,
      validUntil: quote.validUntil,
      notes: quote.notes,
      terms: quote.terms,
      createdAt: quote.createdAt,
      updatedAt: quote.updatedAt,
      publicToken: quote.publicToken,
      sentAt: quote.sentAt,
      viewedAt: quote.viewedAt,
      approvedAt: quote.approvedAt,
      declinedAt: quote.declinedAt,
      clientName: quote.clientName,
      propertyAddress: quote.propertyAddress,
      createdByName: quote.createdByName,
    );
  }

  /// Convert to entity
  Quote toEntity() {
    return Quote(
      id: id,
      clientId: clientId,
      propertyId: propertyId,
      status: status,
      items: items,
      subtotal: subtotal,
      taxRate: taxRate,
      tax: tax,
      total: total,
      validUntil: validUntil,
      notes: notes,
      terms: terms,
      createdAt: createdAt,
      updatedAt: updatedAt,
      publicToken: publicToken,
      sentAt: sentAt,
      viewedAt: viewedAt,
      approvedAt: approvedAt,
      declinedAt: declinedAt,
      clientName: clientName,
      propertyAddress: propertyAddress,
      createdByName: createdByName,
    );
  }
}

/// Quote statistics model
class QuoteStatsModel {
  final int totalQuotes;
  final int draftQuotes;
  final int sentQuotes;
  final int approvedQuotes;
  final double totalValue;
  final double approvalRate;
  final int pendingQuotes;

  const QuoteStatsModel({
    required this.totalQuotes,
    required this.draftQuotes,
    required this.sentQuotes,
    required this.approvedQuotes,
    required this.totalValue,
    required this.approvalRate,
    required this.pendingQuotes,
  });

  factory QuoteStatsModel.empty() => const QuoteStatsModel(
        totalQuotes: 0,
        draftQuotes: 0,
        sentQuotes: 0,
        approvedQuotes: 0,
        totalValue: 0,
        approvalRate: 0,
        pendingQuotes: 0,
      );

  factory QuoteStatsModel.fromQuotes(List<Quote> quotes) {
    int draft = 0;
    int sent = 0;
    int approved = 0;
    double value = 0;

    for (final quote in quotes) {
      value += quote.total;
      switch (quote.status) {
        case QuoteStatus.draft:
          draft++;
          break;
        case QuoteStatus.sent:
        case QuoteStatus.viewed:
          sent++;
          break;
        case QuoteStatus.approved:
          approved++;
          break;
        default:
          break;
      }
    }

    final approvalRate = (sent + approved) == 0
        ? 0.0
        : (approved / (sent + approved)) * 100;

    return QuoteStatsModel(
      totalQuotes: quotes.length,
      draftQuotes: draft,
      sentQuotes: sent,
      approvedQuotes: approved,
      totalValue: value,
      approvalRate: approvalRate,
      pendingQuotes: sent,
    );
  }

  factory QuoteStatsModel.fromJson(Map<String, dynamic> json) {
    return QuoteStatsModel(
      totalQuotes: json['total_quotes'] as int? ?? 0,
      draftQuotes: json['draft_quotes'] as int? ?? 0,
      sentQuotes: json['sent_quotes'] as int? ?? 0,
      approvedQuotes: json['approved_quotes'] as int? ?? 0,
      totalValue: (json['total_value'] as num?)?.toDouble() ?? 0,
      approvalRate: (json['approval_rate'] as num?)?.toDouble() ?? 0,
      pendingQuotes: json['pending_quotes'] as int? ?? 0,
    );
  }
}
