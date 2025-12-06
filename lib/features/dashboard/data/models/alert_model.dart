import 'package:somni_property/features/dashboard/domain/entities/alert.dart';

/// Alert model for JSON serialization
class AlertModel extends Alert {
  const AlertModel({
    required super.id,
    required super.title,
    required super.message,
    required super.priority,
    required super.type,
    required super.createdAt,
    super.actionUrl,
    super.actionLabel,
    super.relatedEntityId,
    super.relatedEntityType,
    super.isDismissible,
  });

  factory AlertModel.fromJson(Map<String, dynamic> json) {
    return AlertModel(
      id: json['id'] as String,
      title: json['title'] as String,
      message: json['message'] as String,
      priority: AlertPriority.fromString(json['priority'] as String? ?? 'medium'),
      type: AlertType.fromString(json['type'] as String? ?? 'system_notification'),
      createdAt: DateTime.parse(json['created_at'] as String),
      actionUrl: json['action_url'] as String?,
      actionLabel: json['action_label'] as String?,
      relatedEntityId: json['related_entity_id'] as String?,
      relatedEntityType: json['related_entity_type'] as String?,
      isDismissible: json['is_dismissible'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'message': message,
      'priority': priority.value,
      'type': type.value,
      'created_at': createdAt.toIso8601String(),
      if (actionUrl != null) 'action_url': actionUrl,
      if (actionLabel != null) 'action_label': actionLabel,
      if (relatedEntityId != null) 'related_entity_id': relatedEntityId,
      if (relatedEntityType != null) 'related_entity_type': relatedEntityType,
      'is_dismissible': isDismissible,
    };
  }

  /// Convert entity to model
  factory AlertModel.fromEntity(Alert alert) {
    return AlertModel(
      id: alert.id,
      title: alert.title,
      message: alert.message,
      priority: alert.priority,
      type: alert.type,
      createdAt: alert.createdAt,
      actionUrl: alert.actionUrl,
      actionLabel: alert.actionLabel,
      relatedEntityId: alert.relatedEntityId,
      relatedEntityType: alert.relatedEntityType,
      isDismissible: alert.isDismissible,
    );
  }

  /// Convert to domain entity
  Alert toEntity() => this;
}

/// Upcoming event model for JSON serialization
class UpcomingEventModel extends UpcomingEvent {
  const UpcomingEventModel({
    required super.id,
    required super.title,
    required super.description,
    required super.scheduledDate,
    required super.type,
    super.relatedEntityId,
    super.relatedEntityType,
  });

  factory UpcomingEventModel.fromJson(Map<String, dynamic> json) {
    return UpcomingEventModel(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String,
      scheduledDate: DateTime.parse(json['scheduled_date'] as String),
      type: EventType.fromString(json['type'] as String? ?? 'other'),
      relatedEntityId: json['related_entity_id'] as String?,
      relatedEntityType: json['related_entity_type'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'scheduled_date': scheduledDate.toIso8601String(),
      'type': type.value,
      if (relatedEntityId != null) 'related_entity_id': relatedEntityId,
      if (relatedEntityType != null) 'related_entity_type': relatedEntityType,
    };
  }

  /// Convert entity to model
  factory UpcomingEventModel.fromEntity(UpcomingEvent event) {
    return UpcomingEventModel(
      id: event.id,
      title: event.title,
      description: event.description,
      scheduledDate: event.scheduledDate,
      type: event.type,
      relatedEntityId: event.relatedEntityId,
      relatedEntityType: event.relatedEntityType,
    );
  }

  /// Convert to domain entity
  UpcomingEvent toEntity() => this;
}
