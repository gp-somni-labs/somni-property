import 'package:equatable/equatable.dart';

/// Tenant entity representing a property tenant/renter
class Tenant extends Equatable {
  final String id;
  final String firstName;
  final String lastName;
  final String email;
  final String phone;
  final String? dateOfBirth;
  final EmergencyContact? emergencyContact;
  final String? currentUnitId;
  final String? currentLeaseId;
  final TenantStatus status;
  final String? notes;
  final String? profileImageUrl;
  final DateTime createdAt;
  final DateTime updatedAt;

  const Tenant({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.email,
    required this.phone,
    this.dateOfBirth,
    this.emergencyContact,
    this.currentUnitId,
    this.currentLeaseId,
    required this.status,
    this.notes,
    this.profileImageUrl,
    required this.createdAt,
    required this.updatedAt,
  });

  /// Get full name
  String get fullName => '$firstName $lastName';

  /// Get initials for avatar
  String get initials {
    final first = firstName.isNotEmpty ? firstName[0].toUpperCase() : '';
    final last = lastName.isNotEmpty ? lastName[0].toUpperCase() : '';
    return '$first$last';
  }

  /// Check if tenant has active lease
  bool get hasActiveLease => currentLeaseId != null && currentUnitId != null;

  /// Get formatted phone number
  String get formattedPhone {
    if (phone.length == 10) {
      return '(${phone.substring(0, 3)}) ${phone.substring(3, 6)}-${phone.substring(6)}';
    }
    return phone;
  }

  @override
  List<Object?> get props => [
        id,
        firstName,
        lastName,
        email,
        phone,
        dateOfBirth,
        emergencyContact,
        currentUnitId,
        currentLeaseId,
        status,
        notes,
        profileImageUrl,
        createdAt,
        updatedAt,
      ];

  Tenant copyWith({
    String? id,
    String? firstName,
    String? lastName,
    String? email,
    String? phone,
    String? dateOfBirth,
    EmergencyContact? emergencyContact,
    String? currentUnitId,
    String? currentLeaseId,
    TenantStatus? status,
    String? notes,
    String? profileImageUrl,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Tenant(
      id: id ?? this.id,
      firstName: firstName ?? this.firstName,
      lastName: lastName ?? this.lastName,
      email: email ?? this.email,
      phone: phone ?? this.phone,
      dateOfBirth: dateOfBirth ?? this.dateOfBirth,
      emergencyContact: emergencyContact ?? this.emergencyContact,
      currentUnitId: currentUnitId ?? this.currentUnitId,
      currentLeaseId: currentLeaseId ?? this.currentLeaseId,
      status: status ?? this.status,
      notes: notes ?? this.notes,
      profileImageUrl: profileImageUrl ?? this.profileImageUrl,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

/// Tenant status
enum TenantStatus {
  active('Active'),
  inactive('Inactive'),
  pending('Pending'),
  evicted('Evicted'),
  movedOut('Moved Out');

  final String displayName;
  const TenantStatus(this.displayName);
}

/// Emergency contact information
class EmergencyContact extends Equatable {
  final String name;
  final String phone;
  final String relationship;

  const EmergencyContact({
    required this.name,
    required this.phone,
    required this.relationship,
  });

  @override
  List<Object?> get props => [name, phone, relationship];

  factory EmergencyContact.fromJson(Map<String, dynamic> json) {
    return EmergencyContact(
      name: json['name'] as String,
      phone: json['phone'] as String,
      relationship: json['relationship'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'phone': phone,
      'relationship': relationship,
    };
  }
}
