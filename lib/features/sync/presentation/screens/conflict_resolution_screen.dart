import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/sync/sync_models.dart';
import '../../../../core/sync/sync_manager.dart';

/// Screen for resolving sync conflicts
class ConflictResolutionScreen extends ConsumerStatefulWidget {
  final SyncConflict conflict;

  const ConflictResolutionScreen({
    Key? key,
    required this.conflict,
  }) : super(key: key);

  @override
  ConsumerState<ConflictResolutionScreen> createState() => _ConflictResolutionScreenState();
}

class _ConflictResolutionScreenState extends ConsumerState<ConflictResolutionScreen> {
  bool _isResolving = false;
  String? _error;

  @override
  Widget build(BuildContext context) {
    final conflict = widget.conflict;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Resolve Conflict'),
        backgroundColor: Theme.of(context).colorScheme.error,
        foregroundColor: Colors.white,
      ),
      body: _isResolving
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Error banner
                  if (_error != null) ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.red.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.red.shade200),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.error_outline, color: Colors.red.shade700),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              _error!,
                              style: TextStyle(color: Colors.red.shade900),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Conflict info card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Conflict Detected',
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'The ${conflict.entityType} was modified on both your device and the server. '
                            'Please choose how to resolve this conflict.',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 12),
                          const Divider(),
                          const SizedBox(height: 12),
                          _buildInfoRow('Entity Type', _formatEntityType(conflict.entityType)),
                          _buildInfoRow('Your Version', conflict.clientVersion.toString()),
                          _buildInfoRow('Server Version', conflict.serverVersion.toString()),
                          _buildInfoRow('Conflicting Fields', conflict.conflictingFields.join(', ')),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Comparison section
                  Text(
                    'Changes Comparison',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),

                  // Side-by-side comparison
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Your changes
                      Expanded(
                        child: _buildDataCard(
                          title: 'Your Changes',
                          data: conflict.clientData,
                          conflictingFields: conflict.conflictingFields,
                          color: Colors.blue,
                        ),
                      ),
                      const SizedBox(width: 12),
                      // Server changes
                      Expanded(
                        child: _buildDataCard(
                          title: 'Server Changes',
                          data: conflict.serverData,
                          conflictingFields: conflict.conflictingFields,
                          color: Colors.orange,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 32),

                  // Resolution options
                  Text(
                    'Resolution Options',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),

                  _buildResolutionButton(
                    icon: Icons.smartphone,
                    title: 'Use My Changes',
                    description: 'Keep your local changes and discard server changes',
                    color: Colors.blue,
                    onPressed: () => _resolveConflict('client_wins'),
                  ),
                  const SizedBox(height: 12),
                  _buildResolutionButton(
                    icon: Icons.cloud,
                    title: 'Use Server Changes',
                    description: 'Accept server changes and discard your local changes',
                    color: Colors.orange,
                    onPressed: () => _resolveConflict('server_wins'),
                  ),
                  const SizedBox(height: 12),
                  _buildResolutionButton(
                    icon: Icons.merge_type,
                    title: 'Merge Manually',
                    description: 'Choose specific fields from each version',
                    color: Colors.purple,
                    onPressed: () => _showMergeDialog(),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 140,
            child: Text(
              label,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
          Expanded(
            child: Text(value),
          ),
        ],
      ),
    );
  }

  Widget _buildDataCard({
    required String title,
    required Map<String, dynamic> data,
    required List<String> conflictingFields,
    required Color color,
  }) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: color.withOpacity(0.5), width: 2),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  title == 'Your Changes' ? Icons.smartphone : Icons.cloud,
                  color: color,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: color,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
            const Divider(),
            ...data.entries.map((entry) {
              final isConflicting = conflictingFields.contains(entry.key);
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 4.0),
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: isConflicting
                      ? BoxDecoration(
                          color: color.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(4),
                        )
                      : null,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (isConflicting)
                        Icon(Icons.warning_amber, size: 16, color: color),
                      if (isConflicting) const SizedBox(width: 4),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _formatFieldName(entry.key),
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: isConflicting ? FontWeight.w600 : FontWeight.normal,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              _formatValue(entry.value),
                              style: const TextStyle(fontSize: 14),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildResolutionButton({
    required IconData icon,
    required String title,
    required String description,
    required Color color,
    required VoidCallback onPressed,
  }) {
    return Card(
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, color: color, size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      description,
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _resolveConflict(String strategy) async {
    setState(() {
      _isResolving = true;
      _error = null;
    });

    try {
      // TODO: Get SyncManager from Riverpod provider
      // final syncManager = ref.read(syncManagerProvider);

      // For now, we'll show a placeholder
      // In production, this would call:
      // await syncManager.resolveConflict(
      //   conflictId: widget.conflict.id,
      //   resolutionStrategy: strategy,
      // );

      await Future.delayed(const Duration(seconds: 1)); // Simulate API call

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Conflict resolved successfully'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      setState(() {
        _error = 'Failed to resolve conflict: $e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isResolving = false;
        });
      }
    }
  }

  void _showMergeDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Manual Merge'),
        content: const Text(
          'Manual merge allows you to pick specific fields from each version. '
          'This feature will be available in a future update.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  String _formatEntityType(String entityType) {
    return entityType
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }

  String _formatFieldName(String fieldName) {
    return fieldName
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }

  String _formatValue(dynamic value) {
    if (value == null) return '(empty)';
    if (value is Map || value is List) return value.toString();
    return value.toString();
  }
}
