import 'package:json_annotation/json_annotation.dart';

part 'sync_models.g.dart';

/// Device Registration Request
@JsonSerializable()
class DeviceRegistrationRequest {
  @JsonKey(name: 'device_id')
  final String deviceId;

  @JsonKey(name: 'device_name')
  final String deviceName;

  final String platform;

  @JsonKey(name: 'app_version')
  final String appVersion;

  @JsonKey(name: 'os_version')
  final String osVersion;

  DeviceRegistrationRequest({
    required this.deviceId,
    required this.deviceName,
    required this.platform,
    required this.appVersion,
    required this.osVersion,
  });

  factory DeviceRegistrationRequest.fromJson(Map<String, dynamic> json) =>
      _$DeviceRegistrationRequestFromJson(json);

  Map<String, dynamic> toJson() => _$DeviceRegistrationRequestToJson(this);
}

/// Device Registration Response
@JsonSerializable()
class DeviceRegistrationResponse {
  @JsonKey(name: 'client_id')
  final String clientId;

  @JsonKey(name: 'device_id')
  final String deviceId;

  @JsonKey(name: 'user_id')
  final String userId;

  @JsonKey(name: 'is_new')
  final bool isNew;

  @JsonKey(name: 'last_sync_at')
  final String? lastSyncAt;

  final String message;

  DeviceRegistrationResponse({
    required this.clientId,
    required this.deviceId,
    required this.userId,
    required this.isNew,
    this.lastSyncAt,
    required this.message,
  });

  factory DeviceRegistrationResponse.fromJson(Map<String, dynamic> json) =>
      _$DeviceRegistrationResponseFromJson(json);

  Map<String, dynamic> toJson() => _$DeviceRegistrationResponseToJson(this);
}

/// Sync Change Model
@JsonSerializable()
class SyncChange {
  final String? id;

  @JsonKey(name: 'entity_type')
  final String entityType;

  @JsonKey(name: 'entity_id')
  final String? entityId;

  final String operation; // CREATE, UPDATE, DELETE

  final Map<String, dynamic>? data;

  @JsonKey(name: 'changed_fields')
  final List<String>? changedFields;

  final int? version;

  @JsonKey(name: 'user_id')
  final String? userId;

  @JsonKey(name: 'created_at')
  final String? createdAt;

  @JsonKey(name: 'local_id')
  final String? localId;

  final String? timestamp;

  SyncChange({
    this.id,
    required this.entityType,
    this.entityId,
    required this.operation,
    this.data,
    this.changedFields,
    this.version,
    this.userId,
    this.createdAt,
    this.localId,
    this.timestamp,
  });

  factory SyncChange.fromJson(Map<String, dynamic> json) =>
      _$SyncChangeFromJson(json);

  Map<String, dynamic> toJson() => _$SyncChangeToJson(this);
}

/// Pull Sync Response
@JsonSerializable()
class PullSyncResponse {
  final List<SyncChange> changes;

  @JsonKey(name: 'sync_timestamp')
  final String syncTimestamp;

  @JsonKey(name: 'has_more')
  final bool hasMore;

  @JsonKey(name: 'next_cursor')
  final String? nextCursor;

  @JsonKey(name: 'total_changes')
  final int totalChanges;

  PullSyncResponse({
    required this.changes,
    required this.syncTimestamp,
    required this.hasMore,
    this.nextCursor,
    required this.totalChanges,
  });

  factory PullSyncResponse.fromJson(Map<String, dynamic> json) =>
      _$PullSyncResponseFromJson(json);

  Map<String, dynamic> toJson() => _$PullSyncResponseToJson(this);
}

/// Push Sync Request
@JsonSerializable()
class PushSyncRequest {
  @JsonKey(name: 'device_id')
  final String deviceId;

  final List<SyncChange> changes;

  @JsonKey(name: 'sync_timestamp')
  final String syncTimestamp;

  PushSyncRequest({
    required this.deviceId,
    required this.changes,
    required this.syncTimestamp,
  });

  factory PushSyncRequest.fromJson(Map<String, dynamic> json) =>
      _$PushSyncRequestFromJson(json);

  Map<String, dynamic> toJson() => _$PushSyncRequestToJson(this);
}

/// Push Sync Result
@JsonSerializable()
class PushSyncResult {
  @JsonKey(name: 'local_id')
  final String? localId;

  @JsonKey(name: 'entity_id')
  final String? entityId;

  @JsonKey(name: 'entity_type')
  final String entityType;

  final String operation;

  final String status; // success, conflict, error

  final int? version;

  @JsonKey(name: 'conflict_id')
  final String? conflictId;

  final String? error;

  PushSyncResult({
    this.localId,
    this.entityId,
    required this.entityType,
    required this.operation,
    required this.status,
    this.version,
    this.conflictId,
    this.error,
  });

  factory PushSyncResult.fromJson(Map<String, dynamic> json) =>
      _$PushSyncResultFromJson(json);

  Map<String, dynamic> toJson() => _$PushSyncResultToJson(this);
}

/// Push Sync Response
@JsonSerializable()
class PushSyncResponse {
  final List<PushSyncResult> results;

  @JsonKey(name: 'sync_timestamp')
  final String syncTimestamp;

  @JsonKey(name: 'total_applied')
  final int totalApplied;

  @JsonKey(name: 'total_conflicts')
  final int totalConflicts;

  @JsonKey(name: 'total_errors')
  final int totalErrors;

  final String message;

  PushSyncResponse({
    required this.results,
    required this.syncTimestamp,
    required this.totalApplied,
    required this.totalConflicts,
    required this.totalErrors,
    required this.message,
  });

  factory PushSyncResponse.fromJson(Map<String, dynamic> json) =>
      _$PushSyncResponseFromJson(json);

  Map<String, dynamic> toJson() => _$PushSyncResponseToJson(this);
}

/// Conflict Model
@JsonSerializable()
class SyncConflict {
  final String id;

  @JsonKey(name: 'entity_type')
  final String entityType;

  @JsonKey(name: 'entity_id')
  final String entityId;

  @JsonKey(name: 'client_version')
  final int clientVersion;

  @JsonKey(name: 'server_version')
  final int serverVersion;

  @JsonKey(name: 'client_data')
  final Map<String, dynamic> clientData;

  @JsonKey(name: 'server_data')
  final Map<String, dynamic> serverData;

  @JsonKey(name: 'conflicting_fields')
  final List<String> conflictingFields;

  final String status;

  @JsonKey(name: 'created_at')
  final String createdAt;

  SyncConflict({
    required this.id,
    required this.entityType,
    required this.entityId,
    required this.clientVersion,
    required this.serverVersion,
    required this.clientData,
    required this.serverData,
    required this.conflictingFields,
    required this.status,
    required this.createdAt,
  });

  factory SyncConflict.fromJson(Map<String, dynamic> json) =>
      _$SyncConflictFromJson(json);

  Map<String, dynamic> toJson() => _$SyncConflictToJson(this);
}

/// Conflicts Response
@JsonSerializable()
class ConflictsResponse {
  final List<SyncConflict> conflicts;

  @JsonKey(name: 'total_pending')
  final int totalPending;

  @JsonKey(name: 'total_resolved')
  final int totalResolved;

  ConflictsResponse({
    required this.conflicts,
    required this.totalPending,
    required this.totalResolved,
  });

  factory ConflictsResponse.fromJson(Map<String, dynamic> json) =>
      _$ConflictsResponseFromJson(json);

  Map<String, dynamic> toJson() => _$ConflictsResponseToJson(this);
}

/// Conflict Resolution Request
@JsonSerializable()
class ConflictResolutionRequest {
  @JsonKey(name: 'conflict_id')
  final String conflictId;

  @JsonKey(name: 'resolution_strategy')
  final String resolutionStrategy; // client_wins, server_wins, merge, manual

  @JsonKey(name: 'resolved_data')
  final Map<String, dynamic>? resolvedData;

  ConflictResolutionRequest({
    required this.conflictId,
    required this.resolutionStrategy,
    this.resolvedData,
  });

  factory ConflictResolutionRequest.fromJson(Map<String, dynamic> json) =>
      _$ConflictResolutionRequestFromJson(json);

  Map<String, dynamic> toJson() => _$ConflictResolutionRequestToJson(this);
}

/// Conflict Resolution Response
@JsonSerializable()
class ConflictResolutionResponse {
  @JsonKey(name: 'conflict_id')
  final String conflictId;

  final String status;

  @JsonKey(name: 'entity_id')
  final String entityId;

  @JsonKey(name: 'entity_type')
  final String entityType;

  @JsonKey(name: 'new_version')
  final int newVersion;

  final String message;

  ConflictResolutionResponse({
    required this.conflictId,
    required this.status,
    required this.entityId,
    required this.entityType,
    required this.newVersion,
    required this.message,
  });

  factory ConflictResolutionResponse.fromJson(Map<String, dynamic> json) =>
      _$ConflictResolutionResponseFromJson(json);

  Map<String, dynamic> toJson() => _$ConflictResolutionResponseToJson(this);
}

/// Sync Status Response
@JsonSerializable()
class SyncStatusResponse {
  @JsonKey(name: 'client_id')
  final String clientId;

  @JsonKey(name: 'device_id')
  final String deviceId;

  @JsonKey(name: 'device_name')
  final String deviceName;

  @JsonKey(name: 'last_sync_at')
  final String? lastSyncAt;

  @JsonKey(name: 'last_pull_at')
  final String? lastPullAt;

  @JsonKey(name: 'last_push_at')
  final String? lastPushAt;

  @JsonKey(name: 'pending_conflicts')
  final int pendingConflicts;

  @JsonKey(name: 'is_active')
  final bool isActive;

  @JsonKey(name: 'created_at')
  final String createdAt;

  SyncStatusResponse({
    required this.clientId,
    required this.deviceId,
    required this.deviceName,
    this.lastSyncAt,
    this.lastPullAt,
    this.lastPushAt,
    required this.pendingConflicts,
    required this.isActive,
    required this.createdAt,
  });

  factory SyncStatusResponse.fromJson(Map<String, dynamic> json) =>
      _$SyncStatusResponseFromJson(json);

  Map<String, dynamic> toJson() => _$SyncStatusResponseToJson(this);
}

/// Entity Types Response
@JsonSerializable()
class EntityTypesResponse {
  @JsonKey(name: 'entity_types')
  final List<EntityTypeInfo> entityTypes;

  EntityTypesResponse({
    required this.entityTypes,
  });

  factory EntityTypesResponse.fromJson(Map<String, dynamic> json) =>
      _$EntityTypesResponseFromJson(json);

  Map<String, dynamic> toJson() => _$EntityTypesResponseToJson(this);
}

/// Entity Type Info
@JsonSerializable()
class EntityTypeInfo {
  @JsonKey(name: 'entity_type')
  final String entityType;

  @JsonKey(name: 'display_name')
  final String displayName;

  @JsonKey(name: 'is_syncable')
  final bool isSyncable;

  @JsonKey(name: 'requires_permission')
  final String? requiresPermission;

  EntityTypeInfo({
    required this.entityType,
    required this.displayName,
    required this.isSyncable,
    this.requiresPermission,
  });

  factory EntityTypeInfo.fromJson(Map<String, dynamic> json) =>
      _$EntityTypeInfoFromJson(json);

  Map<String, dynamic> toJson() => _$EntityTypeInfoToJson(this);
}
