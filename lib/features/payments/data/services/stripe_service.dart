import 'package:flutter_stripe/flutter_stripe.dart';
import 'package:logger/logger.dart';
import 'package:somni_property/core/network/api_client.dart';

/// Service for handling Stripe payment operations
class StripeService {
  final ApiClient _apiClient;
  final Logger _logger = Logger();

  static const String _baseEndpoint = '/api/v1/payments';

  StripeService(this._apiClient);

  /// Initialize Stripe with publishable key
  static Future<void> initialize(String publishableKey) async {
    Stripe.publishableKey = publishableKey;
    await Stripe.instance.applySettings();
  }

  /// Create a payment intent on the backend
  /// Returns the client secret needed for frontend confirmation
  Future<PaymentIntentResult> createPaymentIntent({
    required String paymentId,
    required double amount,
    required String currency,
    String? customerId,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final response = await _apiClient.post(
        '$_baseEndpoint/$paymentId/stripe/create-intent',
        data: {
          'amount': (amount * 100).toInt(), // Convert to cents
          'currency': currency,
          if (customerId != null) 'customer_id': customerId,
          if (metadata != null) 'metadata': metadata,
        },
      );

      final data = response.data as Map<String, dynamic>;
      return PaymentIntentResult(
        clientSecret: data['client_secret'] as String,
        paymentIntentId: data['payment_intent_id'] as String,
        ephemeralKey: data['ephemeral_key'] as String?,
        customerId: data['customer_id'] as String?,
      );
    } catch (e) {
      _logger.e('Error creating payment intent: $e');
      rethrow;
    }
  }

  /// Present payment sheet and process payment
  Future<StripePaymentResult> presentPaymentSheet({
    required String clientSecret,
    required String paymentIntentId,
    String? merchantDisplayName,
  }) async {
    try {
      // Initialize payment sheet
      await Stripe.instance.initPaymentSheet(
        paymentSheetParameters: SetupPaymentSheetParameters(
          paymentIntentClientSecret: clientSecret,
          merchantDisplayName: merchantDisplayName ?? 'SomniProperty',
          style: ThemeMode.system,
          appearance: const PaymentSheetAppearance(
            colors: PaymentSheetAppearanceColors(
              primary: Color(0xFF6366F1),
            ),
          ),
        ),
      );

      // Present payment sheet
      await Stripe.instance.presentPaymentSheet();

      _logger.i('Payment sheet completed successfully');
      return StripePaymentResult(
        success: true,
        paymentIntentId: paymentIntentId,
      );
    } on StripeException catch (e) {
      _logger.e('Stripe error: ${e.error.message}');
      return StripePaymentResult(
        success: false,
        error: e.error.message,
        errorCode: e.error.code.toString(),
      );
    } catch (e) {
      _logger.e('Error presenting payment sheet: $e');
      return StripePaymentResult(
        success: false,
        error: 'An unexpected error occurred',
      );
    }
  }

  /// Confirm payment on backend after Stripe confirmation
  Future<void> confirmPaymentOnBackend({
    required String paymentId,
    required String paymentIntentId,
  }) async {
    try {
      await _apiClient.post(
        '$_baseEndpoint/$paymentId/stripe/confirm',
        data: {
          'payment_intent_id': paymentIntentId,
        },
      );
      _logger.i('Payment confirmed on backend');
    } catch (e) {
      _logger.e('Error confirming payment on backend: $e');
      rethrow;
    }
  }

  /// Create and confirm payment in one flow
  Future<StripePaymentResult> processPayment({
    required String paymentId,
    required double amount,
    required String currency,
    String? customerId,
    Map<String, dynamic>? metadata,
    String? merchantDisplayName,
  }) async {
    try {
      // Step 1: Create payment intent
      final intentResult = await createPaymentIntent(
        paymentId: paymentId,
        amount: amount,
        currency: currency,
        customerId: customerId,
        metadata: metadata,
      );

      // Step 2: Present payment sheet
      final paymentResult = await presentPaymentSheet(
        clientSecret: intentResult.clientSecret,
        paymentIntentId: intentResult.paymentIntentId,
        merchantDisplayName: merchantDisplayName,
      );

      if (!paymentResult.success) {
        return paymentResult;
      }

      // Step 3: Confirm on backend
      await confirmPaymentOnBackend(
        paymentId: paymentId,
        paymentIntentId: intentResult.paymentIntentId,
      );

      return paymentResult;
    } catch (e) {
      _logger.e('Error processing payment: $e');
      return StripePaymentResult(
        success: false,
        error: 'Failed to process payment: $e',
      );
    }
  }

  /// Retrieve payment intent status
  Future<String?> getPaymentIntentStatus(String paymentIntentId) async {
    try {
      final paymentIntent = await Stripe.instance.retrievePaymentIntent(
        paymentIntentId,
      );
      return paymentIntent.status.toString();
    } catch (e) {
      _logger.e('Error retrieving payment intent: $e');
      return null;
    }
  }

  /// Process refund on backend
  Future<void> processRefund({
    required String paymentId,
    required double amount,
    String? reason,
  }) async {
    try {
      await _apiClient.post(
        '$_baseEndpoint/$paymentId/stripe/refund',
        data: {
          'amount': (amount * 100).toInt(), // Convert to cents
          if (reason != null) 'reason': reason,
        },
      );
      _logger.i('Refund processed successfully');
    } catch (e) {
      _logger.e('Error processing refund: $e');
      rethrow;
    }
  }
}

/// Result from creating a payment intent
class PaymentIntentResult {
  final String clientSecret;
  final String paymentIntentId;
  final String? ephemeralKey;
  final String? customerId;

  PaymentIntentResult({
    required this.clientSecret,
    required this.paymentIntentId,
    this.ephemeralKey,
    this.customerId,
  });
}

/// Result from Stripe payment process
class StripePaymentResult {
  final bool success;
  final String? paymentIntentId;
  final String? error;
  final String? errorCode;

  StripePaymentResult({
    required this.success,
    this.paymentIntentId,
    this.error,
    this.errorCode,
  });
}
