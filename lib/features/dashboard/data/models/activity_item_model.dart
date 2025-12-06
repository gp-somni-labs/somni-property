import 'package:somni_property/features/dashboard/domain/entities/activity_item.dart';

/// Activity item model for JSON serialization
class ActivityItemModel extends ActivityItem {
  const ActivityItemModel({
    required super.id,
    required super.title,
    required super.description,
    required super.type,
    required super.timestamp,
    super.userId,
    super.userName,
    super.relatedEntityId,
    super.relatedEntityType,
    super.metadata,
  });

  factory ActivityItemModel.fromJson(Map<String, dynamic> json) {
    return ActivityItemModel(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String,
      type: ActivityType.fromString(json['type'] as String? ?? 'user_activity'),
      timestamp: DateTime.parse(json['timestamp'] as String),
      userId: json['user_id'] as String?,
      userName: json['user_name'] as String?,
      relatedEntityId: json['related_entity_id'] as String?,
      relatedEntityType: json['related_entity_type'] as String?,
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'type': type.value,
      'timestamp': timestamp.toIso8601String(),
      if (userId != null) 'user_id': userId,
      if (userName != null) 'user_name': userName,
      if (relatedEntityId != null) 'related_entity_id': relatedEntityId,
      if (relatedEntityType != null) 'related_entity_type': relatedEntityType,
      if (metadata != null) 'metadata': metadata,
    };
  }

  /// Convert entity to model
  factory ActivityItemModel.fromEntity(ActivityItem item) {
    return ActivityItemModel(
      id: item.id,
      title: item.title,
      description: item.description,
      type: item.type,
      timestamp: item.timestamp,
      userId: item.userId,
      userName: item.userName,
      relatedEntityId: item.relatedEntityId,
      relatedEntityType: item.relatedEntityType,
      metadata: item.metadata,
    );
  }

  /// Convert to domain entity
  ActivityItem toEntity() => this;
}
