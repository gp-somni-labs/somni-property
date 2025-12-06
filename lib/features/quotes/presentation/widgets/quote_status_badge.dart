import 'package:flutter/material.dart';
import 'package:somni_property/features/quotes/domain/entities/quote.dart';

/// Badge widget for displaying quote status with color coding
class QuoteStatusBadge extends StatelessWidget {
  final QuoteStatus status;
  final bool showIcon;

  const QuoteStatusBadge({
    super.key,
    required this.status,
    this.showIcon = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = _getStatusColors(theme);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showIcon) ...[
            Icon(
              _getStatusIcon(),
              size: 14,
              color: colors.text,
            ),
            const SizedBox(width: 4),
          ],
          Text(
            status.displayName,
            style: theme.textTheme.labelSmall?.copyWith(
              color: colors.text,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  _StatusColors _getStatusColors(ThemeData theme) {
    switch (status) {
      case QuoteStatus.draft:
        return _StatusColors(
          background: theme.colorScheme.surfaceVariant,
          border: theme.colorScheme.outline,
          text: theme.colorScheme.onSurfaceVariant,
        );
      case QuoteStatus.sent:
        return _StatusColors(
          background: Colors.blue.shade50,
          border: Colors.blue.shade200,
          text: Colors.blue.shade700,
        );
      case QuoteStatus.viewed:
        return _StatusColors(
          background: Colors.purple.shade50,
          border: Colors.purple.shade200,
          text: Colors.purple.shade700,
        );
      case QuoteStatus.approved:
        return _StatusColors(
          background: Colors.green.shade50,
          border: Colors.green.shade200,
          text: Colors.green.shade700,
        );
      case QuoteStatus.declined:
        return _StatusColors(
          background: Colors.red.shade50,
          border: Colors.red.shade200,
          text: Colors.red.shade700,
        );
      case QuoteStatus.expired:
        return _StatusColors(
          background: Colors.orange.shade50,
          border: Colors.orange.shade200,
          text: Colors.orange.shade700,
        );
    }
  }

  IconData _getStatusIcon() {
    switch (status) {
      case QuoteStatus.draft:
        return Icons.edit;
      case QuoteStatus.sent:
        return Icons.send;
      case QuoteStatus.viewed:
        return Icons.visibility;
      case QuoteStatus.approved:
        return Icons.check_circle;
      case QuoteStatus.declined:
        return Icons.cancel;
      case QuoteStatus.expired:
        return Icons.event_busy;
    }
  }
}

class _StatusColors {
  final Color background;
  final Color border;
  final Color text;

  _StatusColors({
    required this.background,
    required this.border,
    required this.text,
  });
}
