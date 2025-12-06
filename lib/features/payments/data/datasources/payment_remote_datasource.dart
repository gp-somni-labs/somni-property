import 'package:dio/dio.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/payments/data/models/payment_model.dart';
import 'package:somni_property/features/payments/domain/entities/payment.dart';

/// Remote data source for payment API operations
abstract class PaymentRemoteDataSource {
  /// Get all payments with optional filters
  Future<List<PaymentModel>> getPayments({
    String? leaseId,
    String? tenantId,
    String? unitId,
    PaymentStatus? status,
    PaymentType? type,
    DateTime? fromDate,
    DateTime? toDate,
  });

  /// Get a single payment by ID
  Future<PaymentModel> getPayment(String id);

  /// Get payments by status
  Future<List<PaymentModel>> getPaymentsByStatus(PaymentStatus status);

  /// Get overdue payments
  Future<List<PaymentModel>> getOverduePayments();

  /// Get upcoming payments
  Future<List<PaymentModel>> getUpcomingPayments(int withinDays);

  /// Get payments for a lease
  Future<List<PaymentModel>> getPaymentsForLease(String leaseId);

  /// Get payments for a tenant
  Future<List<PaymentModel>> getPaymentsForTenant(String tenantId);

  /// Get payment statistics
  Future<PaymentStatsModel> getPaymentStats({
    DateTime? fromDate,
    DateTime? toDate,
  });

  /// Create a new payment
  Future<PaymentModel> createPayment(PaymentModel payment);

  /// Update a payment
  Future<PaymentModel> updatePayment(PaymentModel payment);

  /// Record a payment (mark as paid)
  Future<PaymentModel> recordPayment(
    String paymentId,
    DateTime paidDate,
    PaymentMethod method,
    String? transactionId,
  );

  /// Apply late fee
  Future<PaymentModel> applyLateFee(String paymentId, double amount);

  /// Cancel a payment
  Future<PaymentModel> cancelPayment(String paymentId, String reason);

  /// Refund a payment
  Future<PaymentModel> refundPayment(String paymentId, String reason);

  /// Delete a payment
  Future<void> deletePayment(String id);

  /// Generate monthly payments
  Future<List<PaymentModel>> generateMonthlyPayments(int month, int year);

  /// Create Stripe payment intent
  Future<Map<String, dynamic>> createStripePaymentIntent(
    String paymentId,
    double amount,
    String currency,
  );

  /// Process Stripe payment
  Future<PaymentModel> processStripePayment(
    String paymentId,
    String paymentIntentId,
  );

  /// Get payment receipt URL
  Future<String> getPaymentReceipt(String paymentId);
}

/// Implementation of PaymentRemoteDataSource using Dio
class PaymentRemoteDataSourceImpl implements PaymentRemoteDataSource {
  final ApiClient _apiClient;
  static const String _baseEndpoint = '/api/v1/payments';

  PaymentRemoteDataSourceImpl(this._apiClient);

  @override
  Future<List<PaymentModel>> getPayments({
    String? leaseId,
    String? tenantId,
    String? unitId,
    PaymentStatus? status,
    PaymentType? type,
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    final queryParams = <String, dynamic>{};
    if (leaseId != null) queryParams['lease_id'] = leaseId;
    if (tenantId != null) queryParams['tenant_id'] = tenantId;
    if (unitId != null) queryParams['unit_id'] = unitId;
    if (status != null) queryParams['status'] = status.name;
    if (type != null) queryParams['type'] = type.name;
    if (fromDate != null) queryParams['from_date'] = fromDate.toIso8601String();
    if (toDate != null) queryParams['to_date'] = toDate.toIso8601String();

    final response = await _apiClient.get(
      _baseEndpoint,
      queryParameters: queryParams,
    );

    final data = response.data;
    if (data is List) {
      return data.map((json) => PaymentModel.fromJson(json)).toList();
    } else if (data is Map && data['payments'] != null) {
      return (data['payments'] as List)
          .map((json) => PaymentModel.fromJson(json))
          .toList();
    } else if (data is Map && data['data'] != null) {
      return (data['data'] as List)
          .map((json) => PaymentModel.fromJson(json))
          .toList();
    }

    return [];
  }

  @override
  Future<PaymentModel> getPayment(String id) async {
    final response = await _apiClient.get('$_baseEndpoint/$id');
    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['payment'] != null) {
        return PaymentModel.fromJson(data['payment']);
      }
      return PaymentModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<List<PaymentModel>> getPaymentsByStatus(PaymentStatus status) async {
    return getPayments(status: status);
  }

  @override
  Future<List<PaymentModel>> getOverduePayments() async {
    final response = await _apiClient.get('$_baseEndpoint/overdue');
    final data = response.data;
    if (data is List) {
      return data.map((json) => PaymentModel.fromJson(json)).toList();
    } else if (data is Map && data['payments'] != null) {
      return (data['payments'] as List)
          .map((json) => PaymentModel.fromJson(json))
          .toList();
    }
    return [];
  }

  @override
  Future<List<PaymentModel>> getUpcomingPayments(int withinDays) async {
    final response = await _apiClient.get(
      '$_baseEndpoint/upcoming',
      queryParameters: {'within_days': withinDays},
    );
    final data = response.data;
    if (data is List) {
      return data.map((json) => PaymentModel.fromJson(json)).toList();
    } else if (data is Map && data['payments'] != null) {
      return (data['payments'] as List)
          .map((json) => PaymentModel.fromJson(json))
          .toList();
    }
    return [];
  }

  @override
  Future<List<PaymentModel>> getPaymentsForLease(String leaseId) async {
    return getPayments(leaseId: leaseId);
  }

  @override
  Future<List<PaymentModel>> getPaymentsForTenant(String tenantId) async {
    return getPayments(tenantId: tenantId);
  }

  @override
  Future<PaymentStatsModel> getPaymentStats({
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    final queryParams = <String, dynamic>{};
    if (fromDate != null) queryParams['from_date'] = fromDate.toIso8601String();
    if (toDate != null) queryParams['to_date'] = toDate.toIso8601String();

    final response = await _apiClient.get(
      '$_baseEndpoint/stats',
      queryParameters: queryParams,
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      return PaymentStatsModel.fromJson(data);
    }
    return PaymentStatsModel.empty();
  }

  @override
  Future<PaymentModel> createPayment(PaymentModel payment) async {
    final response = await _apiClient.post(
      _baseEndpoint,
      data: payment.toJson(),
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['payment'] != null) {
        return PaymentModel.fromJson(data['payment']);
      }
      return PaymentModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<PaymentModel> updatePayment(PaymentModel payment) async {
    final response = await _apiClient.put(
      '$_baseEndpoint/${payment.id}',
      data: payment.toJson(),
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['payment'] != null) {
        return PaymentModel.fromJson(data['payment']);
      }
      return PaymentModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<PaymentModel> recordPayment(
    String paymentId,
    DateTime paidDate,
    PaymentMethod method,
    String? transactionId,
  ) async {
    final response = await _apiClient.post(
      '$_baseEndpoint/$paymentId/record',
      data: {
        'paid_date': paidDate.toIso8601String(),
        'method': method.name,
        if (transactionId != null) 'transaction_id': transactionId,
      },
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['payment'] != null) {
        return PaymentModel.fromJson(data['payment']);
      }
      return PaymentModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<PaymentModel> applyLateFee(String paymentId, double amount) async {
    final response = await _apiClient.post(
      '$_baseEndpoint/$paymentId/late-fee',
      data: {'amount': amount},
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['payment'] != null) {
        return PaymentModel.fromJson(data['payment']);
      }
      return PaymentModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<PaymentModel> cancelPayment(String paymentId, String reason) async {
    final response = await _apiClient.post(
      '$_baseEndpoint/$paymentId/cancel',
      data: {'reason': reason},
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['payment'] != null) {
        return PaymentModel.fromJson(data['payment']);
      }
      return PaymentModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<PaymentModel> refundPayment(String paymentId, String reason) async {
    final response = await _apiClient.post(
      '$_baseEndpoint/$paymentId/refund',
      data: {'reason': reason},
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['payment'] != null) {
        return PaymentModel.fromJson(data['payment']);
      }
      return PaymentModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<void> deletePayment(String id) async {
    await _apiClient.delete('$_baseEndpoint/$id');
  }

  @override
  Future<List<PaymentModel>> generateMonthlyPayments(int month, int year) async {
    final response = await _apiClient.post(
      '$_baseEndpoint/generate-monthly',
      data: {
        'month': month,
        'year': year,
      },
    );

    final data = response.data;
    if (data is List) {
      return data.map((json) => PaymentModel.fromJson(json)).toList();
    } else if (data is Map && data['payments'] != null) {
      return (data['payments'] as List)
          .map((json) => PaymentModel.fromJson(json))
          .toList();
    }
    return [];
  }

  @override
  Future<Map<String, dynamic>> createStripePaymentIntent(
    String paymentId,
    double amount,
    String currency,
  ) async {
    final response = await _apiClient.post(
      '$_baseEndpoint/$paymentId/stripe/create-intent',
      data: {
        'amount': (amount * 100).toInt(), // Convert to cents
        'currency': currency,
      },
    );

    return response.data as Map<String, dynamic>;
  }

  @override
  Future<PaymentModel> processStripePayment(
    String paymentId,
    String paymentIntentId,
  ) async {
    final response = await _apiClient.post(
      '$_baseEndpoint/$paymentId/stripe/confirm',
      data: {
        'payment_intent_id': paymentIntentId,
      },
    );

    final data = response.data;
    if (data is Map<String, dynamic>) {
      if (data['payment'] != null) {
        return PaymentModel.fromJson(data['payment']);
      }
      return PaymentModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  }

  @override
  Future<String> getPaymentReceipt(String paymentId) async {
    final response = await _apiClient.get('$_baseEndpoint/$paymentId/receipt');
    final data = response.data;
    if (data is Map<String, dynamic> && data['receipt_url'] != null) {
      return data['receipt_url'] as String;
    }
    throw Exception('Receipt URL not found');
  }
}
