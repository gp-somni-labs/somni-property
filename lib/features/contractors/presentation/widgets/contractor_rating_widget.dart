import 'package:flutter/material.dart';

/// Widget displaying contractor rating with stars
class ContractorRatingWidget extends StatelessWidget {
  final double rating;
  final int? completedJobs;
  final bool showCount;
  final double size;

  const ContractorRatingWidget({
    super.key,
    required this.rating,
    this.completedJobs,
    this.showCount = true,
    this.size = 16,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Rating stars
        ...List.generate(5, (index) {
          if (index < rating.floor()) {
            // Full star
            return Icon(
              Icons.star,
              color: Colors.amber[700],
              size: size,
            );
          } else if (index < rating && rating % 1 != 0) {
            // Half star
            return Icon(
              Icons.star_half,
              color: Colors.amber[700],
              size: size,
            );
          } else {
            // Empty star
            return Icon(
              Icons.star_border,
              color: Colors.amber[700],
              size: size,
            );
          }
        }),
        const SizedBox(width: 4),

        // Rating value
        Text(
          rating.toStringAsFixed(1),
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
        ),

        // Completed jobs count
        if (showCount && completedJobs != null) ...[
          Text(
            ' (${completedJobs!})',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                ),
          ),
        ],
      ],
    );
  }
}
