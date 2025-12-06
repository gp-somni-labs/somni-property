import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/payments/data/services/stripe_service.dart';
import 'package:somni_property/features/payments/domain/entities/payment.dart';
import 'package:somni_property/features/payments/presentation/providers/payment_provider.dart';
import 'package:somni_property/features/payments/presentation/widgets/stripe_payment_dialog.dart';

/// Page for processing a payment with Stripe
class PaymentStripePage extends ConsumerStatefulWidget {
  final String paymentId;

  const PaymentStripePage({super.key, required this.paymentId});

  @override
  ConsumerState<PaymentStripePage> createState() => _PaymentStripePageState();
}

class _PaymentStripePageState extends ConsumerState<PaymentStripePage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _processPayment();
    });
  }

  Future<void> _processPayment() async {
    final state = ref.read(paymentDetailProvider(widget.paymentId));

    if (state.payment == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Payment not found'),
            backgroundColor: Colors.red,
          ),
        );
        context.pop();
      }
      return;
    }

    final payment = state.payment!;

    // Create Stripe service
    final apiClient = ref.read(apiClientProvider);
    final stripeService = StripeService(apiClient);

    // Show payment dialog
    final success = await showStripePaymentDialog(
      context: context,
      payment: payment,
      stripeService: stripeService,
    );

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Payment processed successfully'),
            backgroundColor: Colors.green,
          ),
        );
        // Refresh payment details
        ref.read(paymentDetailProvider(widget.paymentId).notifier).refresh();
        ref.read(paymentsProvider.notifier).loadPayments();
      }
      context.pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Processing Payment'),
      ),
      body: const Center(
        child: CircularProgressIndicator(),
      ),
    );
  }
}
