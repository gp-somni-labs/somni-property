import 'package:equatable/equatable.dart';

/// Contractor entity representing a service provider/contractor
class Contractor extends Equatable {
  final String id;
  final String firstName;
  final String lastName;
  final String company;
  final String email;
  final String phone;
  final String specialty;
  final ContractorStatus status;
  final double hourlyRate;
  final double overtimeRate;
  final double rating;
  final int completedJobs;
  final int activeJobs;
  final List<String> skills;
  final List<Certification> certifications;
  final Availability? availability;
  final String? notes;
  final String? profileImageUrl;
  final DateTime createdAt;
  final DateTime updatedAt;

  const Contractor({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.company,
    required this.email,
    required this.phone,
    required this.specialty,
    required this.status,
    required this.hourlyRate,
    required this.overtimeRate,
    this.rating = 0.0,
    this.completedJobs = 0,
    this.activeJobs = 0,
    this.skills = const [],
    this.certifications = const [],
    this.availability,
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

  /// Check if contractor has active jobs
  bool get hasActiveJobs => activeJobs > 0;

  /// Check if contractor is available
  bool get isAvailable => status == ContractorStatus.active && availability?.isAvailableNow == true;

  /// Get formatted phone number
  String get formattedPhone {
    if (phone.length == 10) {
      return '(${phone.substring(0, 3)}) ${phone.substring(3, 6)}-${phone.substring(6)}';
    }
    return phone;
  }

  /// Calculate average rating (already stored but can be recalculated)
  double get averageRating => rating;

  /// Get rating as integer for star display
  int get ratingStars => rating.round();

  /// Get completion rate percentage
  double get completionRate {
    final total = completedJobs + activeJobs;
    if (total == 0) return 0;
    return (completedJobs / total) * 100;
  }

  /// Check if any certifications are expiring soon (within 30 days)
  bool get hasCertificationsExpiringSoon {
    final now = DateTime.now();
    final thirtyDaysFromNow = now.add(const Duration(days: 30));
    return certifications.any((cert) =>
        cert.expiryDate != null &&
        cert.expiryDate!.isAfter(now) &&
        cert.expiryDate!.isBefore(thirtyDaysFromNow));
  }

  /// Get list of expired certifications
  List<Certification> get expiredCertifications {
    final now = DateTime.now();
    return certifications.where((cert) =>
        cert.expiryDate != null && cert.expiryDate!.isBefore(now)).toList();
  }

  @override
  List<Object?> get props => [
        id,
        firstName,
        lastName,
        company,
        email,
        phone,
        specialty,
        status,
        hourlyRate,
        overtimeRate,
        rating,
        completedJobs,
        activeJobs,
        skills,
        certifications,
        availability,
        notes,
        profileImageUrl,
        createdAt,
        updatedAt,
      ];

  Contractor copyWith({
    String? id,
    String? firstName,
    String? lastName,
    String? company,
    String? email,
    String? phone,
    String? specialty,
    ContractorStatus? status,
    double? hourlyRate,
    double? overtimeRate,
    double? rating,
    int? completedJobs,
    int? activeJobs,
    List<String>? skills,
    List<Certification>? certifications,
    Availability? availability,
    String? notes,
    String? profileImageUrl,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Contractor(
      id: id ?? this.id,
      firstName: firstName ?? this.firstName,
      lastName: lastName ?? this.lastName,
      company: company ?? this.company,
      email: email ?? this.email,
      phone: phone ?? this.phone,
      specialty: specialty ?? this.specialty,
      status: status ?? this.status,
      hourlyRate: hourlyRate ?? this.hourlyRate,
      overtimeRate: overtimeRate ?? this.overtimeRate,
      rating: rating ?? this.rating,
      completedJobs: completedJobs ?? this.completedJobs,
      activeJobs: activeJobs ?? this.activeJobs,
      skills: skills ?? this.skills,
      certifications: certifications ?? this.certifications,
      availability: availability ?? this.availability,
      notes: notes ?? this.notes,
      profileImageUrl: profileImageUrl ?? this.profileImageUrl,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

/// Contractor status
enum ContractorStatus {
  active('Active'),
  inactive('Inactive'),
  suspended('Suspended');

  final String displayName;
  const ContractorStatus(this.displayName);
}

/// Certification information
class Certification extends Equatable {
  final String name;
  final String? issuingAuthority;
  final DateTime? issueDate;
  final DateTime? expiryDate;
  final String? certificateNumber;

  const Certification({
    required this.name,
    this.issuingAuthority,
    this.issueDate,
    this.expiryDate,
    this.certificateNumber,
  });

  /// Check if certification is expired
  bool get isExpired {
    if (expiryDate == null) return false;
    return DateTime.now().isAfter(expiryDate!);
  }

  /// Check if certification is expiring soon (within 30 days)
  bool get isExpiringSoon {
    if (expiryDate == null) return false;
    final now = DateTime.now();
    final thirtyDaysFromNow = now.add(const Duration(days: 30));
    return expiryDate!.isAfter(now) && expiryDate!.isBefore(thirtyDaysFromNow);
  }

  /// Get days until expiry
  int? get daysUntilExpiry {
    if (expiryDate == null) return null;
    return expiryDate!.difference(DateTime.now()).inDays;
  }

  @override
  List<Object?> get props => [
        name,
        issuingAuthority,
        issueDate,
        expiryDate,
        certificateNumber,
      ];

  factory Certification.fromJson(Map<String, dynamic> json) {
    return Certification(
      name: json['name'] as String,
      issuingAuthority: json['issuing_authority'] as String?,
      issueDate: json['issue_date'] != null
          ? DateTime.parse(json['issue_date'] as String)
          : null,
      expiryDate: json['expiry_date'] != null
          ? DateTime.parse(json['expiry_date'] as String)
          : null,
      certificateNumber: json['certificate_number'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      if (issuingAuthority != null) 'issuing_authority': issuingAuthority,
      if (issueDate != null) 'issue_date': issueDate!.toIso8601String(),
      if (expiryDate != null) 'expiry_date': expiryDate!.toIso8601String(),
      if (certificateNumber != null) 'certificate_number': certificateNumber,
    };
  }
}

/// Availability schedule for contractor
class Availability extends Equatable {
  final Map<String, DayAvailability> schedule;
  final List<TimeOff> timeOff;

  const Availability({
    required this.schedule,
    this.timeOff = const [],
  });

  /// Check if contractor is available now
  bool get isAvailableNow {
    final now = DateTime.now();
    final dayName = _getDayName(now.weekday);

    // Check if on time off
    for (final off in timeOff) {
      if (now.isAfter(off.startDate) && now.isBefore(off.endDate)) {
        return false;
      }
    }

    // Check day availability
    final dayAvail = schedule[dayName];
    if (dayAvail == null || !dayAvail.isAvailable) return false;

    // Check time range if specified
    if (dayAvail.startTime != null && dayAvail.endTime != null) {
      final currentTime = TimeOfDay.fromDateTime(now);
      return _isTimeBetween(currentTime, dayAvail.startTime!, dayAvail.endTime!);
    }

    return true;
  }

  String _getDayName(int weekday) {
    const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    return days[weekday - 1];
  }

  bool _isTimeBetween(TimeOfDay time, TimeOfDay start, TimeOfDay end) {
    final timeMinutes = time.hour * 60 + time.minute;
    final startMinutes = start.hour * 60 + start.minute;
    final endMinutes = end.hour * 60 + end.minute;
    return timeMinutes >= startMinutes && timeMinutes <= endMinutes;
  }

  @override
  List<Object?> get props => [schedule, timeOff];

  factory Availability.fromJson(Map<String, dynamic> json) {
    final scheduleMap = <String, DayAvailability>{};
    if (json['schedule'] != null) {
      (json['schedule'] as Map<String, dynamic>).forEach((key, value) {
        scheduleMap[key] = DayAvailability.fromJson(value as Map<String, dynamic>);
      });
    }

    final timeOffList = <TimeOff>[];
    if (json['time_off'] != null) {
      timeOffList.addAll((json['time_off'] as List<dynamic>)
          .map((e) => TimeOff.fromJson(e as Map<String, dynamic>)));
    }

    return Availability(
      schedule: scheduleMap,
      timeOff: timeOffList,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'schedule': schedule.map((key, value) => MapEntry(key, value.toJson())),
      'time_off': timeOff.map((e) => e.toJson()).toList(),
    };
  }
}

/// Day availability
class DayAvailability extends Equatable {
  final bool isAvailable;
  final TimeOfDay? startTime;
  final TimeOfDay? endTime;

  const DayAvailability({
    required this.isAvailable,
    this.startTime,
    this.endTime,
  });

  @override
  List<Object?> get props => [isAvailable, startTime, endTime];

  factory DayAvailability.fromJson(Map<String, dynamic> json) {
    return DayAvailability(
      isAvailable: json['is_available'] as bool,
      startTime: json['start_time'] != null
          ? _parseTimeOfDay(json['start_time'] as String)
          : null,
      endTime: json['end_time'] != null
          ? _parseTimeOfDay(json['end_time'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'is_available': isAvailable,
      if (startTime != null) 'start_time': _formatTimeOfDay(startTime!),
      if (endTime != null) 'end_time': _formatTimeOfDay(endTime!),
    };
  }

  static TimeOfDay _parseTimeOfDay(String time) {
    final parts = time.split(':');
    return TimeOfDay(
      hour: int.parse(parts[0]),
      minute: int.parse(parts[1]),
    );
  }

  static String _formatTimeOfDay(TimeOfDay time) {
    return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
  }
}

/// Time off period
class TimeOff extends Equatable {
  final DateTime startDate;
  final DateTime endDate;
  final String? reason;

  const TimeOff({
    required this.startDate,
    required this.endDate,
    this.reason,
  });

  @override
  List<Object?> get props => [startDate, endDate, reason];

  factory TimeOff.fromJson(Map<String, dynamic> json) {
    return TimeOff(
      startDate: DateTime.parse(json['start_date'] as String),
      endDate: DateTime.parse(json['end_date'] as String),
      reason: json['reason'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'start_date': startDate.toIso8601String(),
      'end_date': endDate.toIso8601String(),
      if (reason != null) 'reason': reason,
    };
  }
}

/// TimeOfDay helper class for time representation
class TimeOfDay extends Equatable {
  final int hour;
  final int minute;

  const TimeOfDay({required this.hour, required this.minute});

  @override
  List<Object?> get props => [hour, minute];

  factory TimeOfDay.fromDateTime(DateTime dateTime) {
    return TimeOfDay(hour: dateTime.hour, minute: dateTime.minute);
  }
}

/// Labor time entry for tracking contractor work
class LaborTime extends Equatable {
  final String id;
  final String contractorId;
  final String workOrderId;
  final DateTime date;
  final double hoursWorked;
  final double overtimeHours;
  final double regularCost;
  final double overtimeCost;
  final double totalCost;
  final String? description;
  final DateTime createdAt;

  const LaborTime({
    required this.id,
    required this.contractorId,
    required this.workOrderId,
    required this.date,
    required this.hoursWorked,
    this.overtimeHours = 0.0,
    required this.regularCost,
    this.overtimeCost = 0.0,
    required this.totalCost,
    this.description,
    required this.createdAt,
  });

  /// Get regular hours (excluding overtime)
  double get regularHours => hoursWorked - overtimeHours;

  @override
  List<Object?> get props => [
        id,
        contractorId,
        workOrderId,
        date,
        hoursWorked,
        overtimeHours,
        regularCost,
        overtimeCost,
        totalCost,
        description,
        createdAt,
      ];
}

/// Contractor performance metrics
class ContractorPerformance extends Equatable {
  final String contractorId;
  final double averageRating;
  final int totalJobs;
  final int completedJobs;
  final int activeJobs;
  final double averageCompletionTime;
  final double onTimePercentage;
  final double totalRevenue;

  const ContractorPerformance({
    required this.contractorId,
    required this.averageRating,
    required this.totalJobs,
    required this.completedJobs,
    required this.activeJobs,
    required this.averageCompletionTime,
    required this.onTimePercentage,
    required this.totalRevenue,
  });

  @override
  List<Object?> get props => [
        contractorId,
        averageRating,
        totalJobs,
        completedJobs,
        activeJobs,
        averageCompletionTime,
        onTimePercentage,
        totalRevenue,
      ];
}

/// Contractor rating/review
class ContractorRating extends Equatable {
  final String id;
  final String contractorId;
  final String workOrderId;
  final int rating;
  final int qualityRating;
  final int communicationRating;
  final int timelinessRating;
  final String? review;
  final String? reviewerName;
  final DateTime createdAt;

  const ContractorRating({
    required this.id,
    required this.contractorId,
    required this.workOrderId,
    required this.rating,
    required this.qualityRating,
    required this.communicationRating,
    required this.timelinessRating,
    this.review,
    this.reviewerName,
    required this.createdAt,
  });

  /// Get average of all ratings
  double get averageRating {
    return (rating + qualityRating + communicationRating + timelinessRating) / 4.0;
  }

  @override
  List<Object?> get props => [
        id,
        contractorId,
        workOrderId,
        rating,
        qualityRating,
        communicationRating,
        timelinessRating,
        review,
        reviewerName,
        createdAt,
      ];
}
