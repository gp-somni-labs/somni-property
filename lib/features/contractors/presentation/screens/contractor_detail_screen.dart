import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:somni_property/features/contractors/presentation/providers/contractor_provider.dart';
import 'package:somni_property/features/contractors/presentation/widgets/contractor_rating_widget.dart';
import 'package:somni_property/features/contractors/presentation/widgets/contractor_performance_card.dart';

/// Contractor detail screen showing profile, metrics, and actions
class ContractorDetailScreen extends ConsumerWidget {
  final String contractorId;

  const ContractorDetailScreen({
    super.key,
    required this.contractorId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailState = ref.watch(contractorDetailProvider(contractorId));
    final contractor = detailState.contractor;

    return Scaffold(
      appBar: AppBar(
        title: Text(contractor?.fullName ?? 'Contractor Details'),
        actions: [
          if (contractor != null) ...[
            IconButton(
              icon: const Icon(Icons.edit),
              onPressed: () => context.go('/contractors/${contractor.id}/edit'),
              tooltip: 'Edit',
            ),
            PopupMenuButton(
              itemBuilder: (context) => [
                const PopupMenuItem(
                  value: 'delete',
                  child: Row(
                    children: [
                      Icon(Icons.delete, color: Colors.red),
                      SizedBox(width: 8),
                      Text('Delete'),
                    ],
                  ),
                ),
              ],
              onSelected: (value) {
                if (value == 'delete') {
                  _confirmDelete(context, ref);
                }
              },
            ),
          ],
        ],
      ),
      body: detailState.isLoading
          ? const Center(child: CircularProgressIndicator())
          : detailState.error != null
              ? _buildErrorState(context, ref, detailState.error!)
              : contractor == null
                  ? _buildEmptyState(context)
                  : RefreshIndicator(
                      onRefresh: () => ref
                          .read(contractorDetailProvider(contractorId).notifier)
                          .refresh(),
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Profile header
                            _buildProfileHeader(context, contractor),
                            const SizedBox(height: 24),

                            // Contact info
                            _buildContactInfo(context, contractor),
                            const SizedBox(height: 24),

                            // Performance metrics
                            if (detailState.performance != null)
                              ContractorPerformanceCard(
                                performance: detailState.performance!,
                              ),
                            const SizedBox(height: 24),

                            // Skills and certifications
                            _buildSkillsAndCertifications(context, contractor),
                            const SizedBox(height: 24),

                            // Labor rates
                            _buildLaborRates(context, contractor),
                            const SizedBox(height: 24),

                            // Active jobs
                            _buildActiveJobs(context, detailState.workOrders),
                            const SizedBox(height: 24),

                            // Ratings
                            if (detailState.ratings.isNotEmpty)
                              _buildRatings(context, detailState.ratings),

                            const SizedBox(height: 80),
                          ],
                        ),
                      ),
                    ),
      floatingActionButton: contractor != null
          ? FloatingActionButton.extended(
              onPressed: () => _showActionMenu(context, ref),
              icon: const Icon(Icons.more_horiz),
              label: const Text('Actions'),
            )
          : null,
    );
  }

  Widget _buildProfileHeader(BuildContext context, contractor) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            // Avatar
            CircleAvatar(
              radius: 40,
              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
              backgroundImage: contractor.profileImageUrl != null
                  ? NetworkImage(contractor.profileImageUrl!)
                  : null,
              child: contractor.profileImageUrl == null
                  ? Text(
                      contractor.initials,
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                        color:
                            Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                    )
                  : null,
            ),
            const SizedBox(width: 16),

            // Name and specialty
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    contractor.fullName,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    contractor.company,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Chip(
                    label: Text(contractor.specialty),
                    avatar: const Icon(Icons.work, size: 16),
                  ),
                  const SizedBox(height: 8),
                  ContractorRatingWidget(
                    rating: contractor.rating,
                    completedJobs: contractor.completedJobs,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContactInfo(BuildContext context, contractor) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Contact Information',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            ListTile(
              leading: const Icon(Icons.email),
              title: Text(contractor.email),
              subtitle: const Text('Email'),
              contentPadding: EdgeInsets.zero,
            ),
            ListTile(
              leading: const Icon(Icons.phone),
              title: Text(contractor.formattedPhone),
              subtitle: const Text('Phone'),
              contentPadding: EdgeInsets.zero,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSkillsAndCertifications(BuildContext context, contractor) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Skills & Certifications',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            if (contractor.skills.isNotEmpty) ...[
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: contractor.skills.map<Widget>((skill) {
                  return Chip(
                    label: Text(skill),
                    backgroundColor:
                        Theme.of(context).colorScheme.secondaryContainer,
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),
            ],
            if (contractor.certifications.isNotEmpty) ...[
              ...contractor.certifications.map((cert) {
                return ListTile(
                  leading: Icon(
                    Icons.verified,
                    color: cert.isExpired
                        ? Colors.red
                        : cert.isExpiringSoon
                            ? Colors.orange
                            : Colors.green,
                  ),
                  title: Text(cert.name),
                  subtitle: cert.expiryDate != null
                      ? Text(
                          cert.isExpired
                              ? 'Expired'
                              : 'Expires: ${cert.expiryDate!.toString().split(' ')[0]}')
                      : null,
                  contentPadding: EdgeInsets.zero,
                );
              }),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildLaborRates(BuildContext context, contractor) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Labor Rates',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _RateCard(
                    label: 'Regular Rate',
                    rate: contractor.hourlyRate,
                    icon: Icons.schedule,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _RateCard(
                    label: 'Overtime Rate',
                    rate: contractor.overtimeRate,
                    icon: Icons.access_time,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActiveJobs(BuildContext context, List<dynamic> workOrders) {
    final activeJobs =
        workOrders.where((wo) => wo['status'] == 'in_progress').toList();

    if (activeJobs.isEmpty) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Active Jobs',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            ...activeJobs.take(5).map((job) {
              return ListTile(
                leading: const Icon(Icons.work_outline),
                title: Text(job['title'] ?? 'Work Order'),
                subtitle: Text(job['property_name'] ?? ''),
                contentPadding: EdgeInsets.zero,
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildRatings(BuildContext context, ratings) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Recent Ratings',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            ...ratings.take(5).map((rating) {
              return ListTile(
                leading: ContractorRatingWidget(
                  rating: rating.rating.toDouble(),
                  showCount: false,
                ),
                title: Text(rating.review ?? 'No review'),
                subtitle: Text(rating.reviewerName ?? 'Anonymous'),
                contentPadding: EdgeInsets.zero,
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState(BuildContext context, WidgetRef ref, String error) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Error Loading Contractor',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              error,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () => ref
                  .read(contractorDetailProvider(contractorId).notifier)
                  .refresh(),
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.engineering_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.primary.withOpacity(0.5),
            ),
            const SizedBox(height: 16),
            Text(
              'Contractor Not Found',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
          ],
        ),
      ),
    );
  }

  void _showActionMenu(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.assignment),
              title: const Text('Assign to Work Order'),
              onTap: () {
                Navigator.pop(context);
                // TODO: Show assign dialog
              },
            ),
            ListTile(
              leading: const Icon(Icons.access_time),
              title: const Text('Track Labor Time'),
              onTap: () {
                Navigator.pop(context);
                // TODO: Show labor time dialog
              },
            ),
            ListTile(
              leading: const Icon(Icons.star),
              title: const Text('Rate Contractor'),
              onTap: () {
                Navigator.pop(context);
                // TODO: Show rating dialog
              },
            ),
          ],
        ),
      ),
    );
  }

  void _confirmDelete(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Contractor'),
        content: const Text(
            'Are you sure you want to delete this contractor? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              // TODO: Implement delete
              Navigator.pop(context);
              context.go('/contractors');
            },
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
}

class _RateCard extends StatelessWidget {
  final String label;
  final double rate;
  final IconData icon;

  const _RateCard({
    required this.label,
    required this.rate,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Icon(icon, color: Theme.of(context).colorScheme.primary),
          const SizedBox(height: 8),
          Text(
            '\$${rate.toStringAsFixed(2)}',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Theme.of(context).colorScheme.primary,
                ),
          ),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
