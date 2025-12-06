import 'package:flutter/material.dart';
import 'package:somni_property/features/payments/domain/entities/payment.dart';

/// Widget displaying an icon for a payment method
class PaymentMethodIcon extends StatelessWidget {
  final PaymentMethod method;
  final double size;
  final Color? color;

  const PaymentMethodIcon({
    super.key,
    required this.method,
    this.size = 24,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final iconColor = color ?? Theme.of(context).colorScheme.primary;

    IconData icon;
    switch (method) {
      case PaymentMethod.cash:
        icon = Icons.money;
        break;
      case PaymentMethod.check:
        icon = Icons.receipt_long;
        break;
      case PaymentMethod.creditCard:
      case PaymentMethod.debitCard:
        icon = Icons.credit_card;
        break;
      case PaymentMethod.bankTransfer:
        icon = Icons.account_balance;
        break;
      case PaymentMethod.online:
        icon = Icons.payment;
        break;
      default:
        icon = Icons.attach_money;
    }

    return Icon(icon, size: size, color: iconColor);
  }
}
