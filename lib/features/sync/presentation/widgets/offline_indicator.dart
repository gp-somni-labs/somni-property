import 'package:flutter/material.dart';

/// Widget that displays connectivity and sync status
class OfflineIndicator extends StatelessWidget {
  final bool isOnline;
  final bool isSyncing;
  final int pendingChanges;
  final DateTime? lastSyncTime;
  final VoidCallback? onTapSync;

  const OfflineIndicator({
    Key? key,
    required this.isOnline,
    this.isSyncing = false,
    this.pendingChanges = 0,
    this.lastSyncTime,
    this.onTapSync,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    // Don't show anything if online and no pending changes
    if (isOnline && pendingChanges == 0 && !isSyncing) {
      return const SizedBox.shrink();
    }

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      child: Material(
        elevation: 4,
        color: _getBackgroundColor(),
        child: InkWell(
          onTap: isOnline && onTapSync != null ? onTapSync : null,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                // Status icon
                _buildStatusIcon(),
                const SizedBox(width: 12),

                // Status text
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        _getStatusText(),
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 14,
                        ),
                      ),
                      if (_getSubtitleText() != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          _getSubtitleText()!,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.9),
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),

                // Action button/indicator
                if (isSyncing)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                else if (isOnline && pendingChanges > 0 && onTapSync != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: const Text(
                      'Sync Now',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatusIcon() {
    if (isSyncing) {
      return const Icon(
        Icons.sync,
        color: Colors.white,
        size: 24,
      );
    } else if (!isOnline) {
      return const Icon(
        Icons.cloud_off,
        color: Colors.white,
        size: 24,
      );
    } else if (pendingChanges > 0) {
      return Stack(
        clipBehavior: Clip.none,
        children: [
          const Icon(
            Icons.cloud_upload,
            color: Colors.white,
            size: 24,
          ),
          Positioned(
            right: -4,
            top: -4,
            child: Container(
              padding: const EdgeInsets.all(4),
              decoration: const BoxDecoration(
                color: Colors.red,
                shape: BoxShape.circle,
              ),
              constraints: const BoxConstraints(
                minWidth: 16,
                minHeight: 16,
              ),
              child: Text(
                pendingChanges > 99 ? '99+' : pendingChanges.toString(),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 9,
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ],
      );
    } else {
      return const Icon(
        Icons.cloud_done,
        color: Colors.white,
        size: 24,
      );
    }
  }

  String _getStatusText() {
    if (isSyncing) {
      return 'Syncing...';
    } else if (!isOnline) {
      return 'Offline Mode';
    } else if (pendingChanges > 0) {
      return '$pendingChanges ${pendingChanges == 1 ? "change" : "changes"} pending';
    } else {
      return 'All changes synced';
    }
  }

  String? _getSubtitleText() {
    if (isSyncing) {
      return 'Uploading changes to server';
    } else if (!isOnline && pendingChanges > 0) {
      return 'Changes will sync when online';
    } else if (isOnline && pendingChanges > 0) {
      return 'Tap to sync now';
    } else if (lastSyncTime != null) {
      return 'Last synced ${_formatLastSyncTime(lastSyncTime!)}';
    }
    return null;
  }

  Color _getBackgroundColor() {
    if (isSyncing) {
      return Colors.blue.shade600;
    } else if (!isOnline) {
      return Colors.orange.shade700;
    } else if (pendingChanges > 0) {
      return Colors.amber.shade700;
    } else {
      return Colors.green.shade600;
    }
  }

  String _formatLastSyncTime(DateTime time) {
    final now = DateTime.now();
    final difference = now.difference(time);

    if (difference.inSeconds < 60) {
      return 'just now';
    } else if (difference.inMinutes < 60) {
      final minutes = difference.inMinutes;
      return '$minutes ${minutes == 1 ? "minute" : "minutes"} ago';
    } else if (difference.inHours < 24) {
      final hours = difference.inHours;
      return '$hours ${hours == 1 ? "hour" : "hours"} ago';
    } else {
      final days = difference.inDays;
      return '$days ${days == 1 ? "day" : "days"} ago';
    }
  }
}

/// Compact version of offline indicator for smaller spaces
class CompactOfflineIndicator extends StatelessWidget {
  final bool isOnline;
  final bool isSyncing;
  final int pendingChanges;

  const CompactOfflineIndicator({
    Key? key,
    required this.isOnline,
    this.isSyncing = false,
    this.pendingChanges = 0,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    IconData icon;
    Color color;

    if (isSyncing) {
      icon = Icons.sync;
      color = Colors.blue;
    } else if (!isOnline) {
      icon = Icons.cloud_off;
      color = Colors.orange;
    } else if (pendingChanges > 0) {
      icon = Icons.cloud_upload;
      color = Colors.amber;
    } else {
      icon = Icons.cloud_done;
      color = Colors.green;
    }

    return Tooltip(
      message: _getTooltipText(),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Icon(icon, color: color, size: 24),
          if (pendingChanges > 0)
            Positioned(
              right: -4,
              top: -4,
              child: Container(
                padding: const EdgeInsets.all(3),
                decoration: const BoxDecoration(
                  color: Colors.red,
                  shape: BoxShape.circle,
                ),
                constraints: const BoxConstraints(
                  minWidth: 14,
                  minHeight: 14,
                ),
                child: Text(
                  pendingChanges > 9 ? '9+' : pendingChanges.toString(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 8,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
        ],
      ),
    );
  }

  String _getTooltipText() {
    if (isSyncing) {
      return 'Syncing...';
    } else if (!isOnline) {
      return 'Offline - changes will sync when online';
    } else if (pendingChanges > 0) {
      return '$pendingChanges ${pendingChanges == 1 ? "change" : "changes"} pending sync';
    } else {
      return 'All changes synced';
    }
  }
}
