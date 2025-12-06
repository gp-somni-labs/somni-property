import 'package:somni_property/features/contractors/domain/entities/contractor.dart';

/// Contractor model for JSON serialization
class ContractorModel extends Contractor {
  const ContractorModel({
    required super.id,
    required super.firstName,
    required super.lastName,
    required super.company,
    required super.email,
    required super.phone,
    required super.specialty,
    required super.status,
    required super.hourlyRate,
    required super.overtimeRate,
    super.rating,
    super.completedJobs,
    super.activeJobs,
    super.skills,
    super.certifications,
    super.availability,
    super.notes,
    super.profileImageUrl,
    required super.createdAt,
    required super.updatedAt,
  });

  factory ContractorModel.fromJson(Map<String, dynamic> json) {
    return ContractorModel(
      id: json['id']?.toString() ?? '',
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
      company: json['company'] as String? ?? '',
      email: json['email'] as String? ?? '',
      phone: json['phone'] as String? ?? '',
      specialty: json['specialty'] as String? ?? '',
      status: ContractorStatus.values.firstWhere(
        (s) => s.name == json['status'],
        orElse: () => ContractorStatus.active,
      ),
      hourlyRate: (json['hourly_rate'] as num?)?.toDouble() ?? 0.0,
      overtimeRate: (json['overtime_rate'] as num?)?.toDouble() ?? 0.0,
      rating: (json['rating'] as num?)?.toDouble() ?? 0.0,
      completedJobs: json['completed_jobs'] as int? ?? 0,
      activeJobs: json['active_jobs'] as int? ?? 0,
      skills: json['skills'] != null
          ? List<String>.from(json['skills'] as List<dynamic>)
          : [],
      certifications: json['certifications'] != null
          ? (json['certifications'] as List<dynamic>)
              .map((e) => Certification.fromJson(e as Map<String, dynamic>))
              .toList()
          : [],
      availability: json['availability'] != null
          ? Availability.fromJson(json['availability'] as Map<String, dynamic>)
          : null,
      notes: json['notes'] as String?,
      profileImageUrl: json['profile_image_url'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'first_name': firstName,
      'last_name': lastName,
      'company': company,
      'email': email,
      'phone': phone,
      'specialty': specialty,
      'status': status.name,
      'hourly_rate': hourlyRate,
      'overtime_rate': overtimeRate,
      'rating': rating,
      'completed_jobs': completedJobs,
      'active_jobs': activeJobs,
      'skills': skills,
      'certifications': certifications.map((c) => c.toJson()).toList(),
      if (availability != null) 'availability': availability!.toJson(),
      if (notes != null) 'notes': notes,
      if (profileImageUrl != null) 'profile_image_url': profileImageUrl,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  /// For creating a new contractor (no ID yet)
  Map<String, dynamic> toCreateJson() {
    final json = toJson();
    json.remove('id');
    json.remove('created_at');
    json.remove('updated_at');
    json.remove('rating');
    json.remove('completed_jobs');
    json.remove('active_jobs');
    return json;
  }

  /// Convert entity to model
  factory ContractorModel.fromEntity(Contractor contractor) {
    return ContractorModel(
      id: contractor.id,
      firstName: contractor.firstName,
      lastName: contractor.lastName,
      company: contractor.company,
      email: contractor.email,
      phone: contractor.phone,
      specialty: contractor.specialty,
      status: contractor.status,
      hourlyRate: contractor.hourlyRate,
      overtimeRate: contractor.overtimeRate,
      rating: contractor.rating,
      completedJobs: contractor.completedJobs,
      activeJobs: contractor.activeJobs,
      skills: contractor.skills,
      certifications: contractor.certifications,
      availability: contractor.availability,
      notes: contractor.notes,
      profileImageUrl: contractor.profileImageUrl,
      createdAt: contractor.createdAt,
      updatedAt: contractor.updatedAt,
    );
  }

  /// Convert to domain entity
  Contractor toEntity() => this;
}

/// Labor time model for JSON serialization
class LaborTimeModel extends LaborTime {
  const LaborTimeModel({
    required super.id,
    required super.contractorId,
    required super.workOrderId,
    required super.date,
    required super.hoursWorked,
    super.overtimeHours,
    required super.regularCost,
    super.overtimeCost,
    required super.totalCost,
    super.description,
    required super.createdAt,
  });

  factory LaborTimeModel.fromJson(Map<String, dynamic> json) {
    return LaborTimeModel(
      id: json['id']?.toString() ?? '',
      contractorId: json['contractor_id']?.toString() ?? '',
      workOrderId: json['work_order_id']?.toString() ?? '',
      date: json['date'] != null
          ? DateTime.parse(json['date'] as String)
          : DateTime.now(),
      hoursWorked: (json['hours_worked'] as num?)?.toDouble() ?? 0.0,
      overtimeHours: (json['overtime_hours'] as num?)?.toDouble() ?? 0.0,
      regularCost: (json['regular_cost'] as num?)?.toDouble() ?? 0.0,
      overtimeCost: (json['overtime_cost'] as num?)?.toDouble() ?? 0.0,
      totalCost: (json['total_cost'] as num?)?.toDouble() ?? 0.0,
      description: json['description'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'contractor_id': contractorId,
      'work_order_id': workOrderId,
      'date': date.toIso8601String(),
      'hours_worked': hoursWorked,
      'overtime_hours': overtimeHours,
      'regular_cost': regularCost,
      'overtime_cost': overtimeCost,
      'total_cost': totalCost,
      if (description != null) 'description': description,
      'created_at': createdAt.toIso8601String(),
    };
  }

  factory LaborTimeModel.fromEntity(LaborTime laborTime) {
    return LaborTimeModel(
      id: laborTime.id,
      contractorId: laborTime.contractorId,
      workOrderId: laborTime.workOrderId,
      date: laborTime.date,
      hoursWorked: laborTime.hoursWorked,
      overtimeHours: laborTime.overtimeHours,
      regularCost: laborTime.regularCost,
      overtimeCost: laborTime.overtimeCost,
      totalCost: laborTime.totalCost,
      description: laborTime.description,
      createdAt: laborTime.createdAt,
    );
  }

  LaborTime toEntity() => this;
}

/// Contractor performance model for JSON serialization
class ContractorPerformanceModel extends ContractorPerformance {
  const ContractorPerformanceModel({
    required super.contractorId,
    required super.averageRating,
    required super.totalJobs,
    required super.completedJobs,
    required super.activeJobs,
    required super.averageCompletionTime,
    required super.onTimePercentage,
    required super.totalRevenue,
  });

  factory ContractorPerformanceModel.fromJson(Map<String, dynamic> json) {
    return ContractorPerformanceModel(
      contractorId: json['contractor_id']?.toString() ?? '',
      averageRating: (json['average_rating'] as num?)?.toDouble() ?? 0.0,
      totalJobs: json['total_jobs'] as int? ?? 0,
      completedJobs: json['completed_jobs'] as int? ?? 0,
      activeJobs: json['active_jobs'] as int? ?? 0,
      averageCompletionTime:
          (json['average_completion_time'] as num?)?.toDouble() ?? 0.0,
      onTimePercentage: (json['on_time_percentage'] as num?)?.toDouble() ?? 0.0,
      totalRevenue: (json['total_revenue'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'contractor_id': contractorId,
      'average_rating': averageRating,
      'total_jobs': totalJobs,
      'completed_jobs': completedJobs,
      'active_jobs': activeJobs,
      'average_completion_time': averageCompletionTime,
      'on_time_percentage': onTimePercentage,
      'total_revenue': totalRevenue,
    };
  }

  factory ContractorPerformanceModel.fromEntity(
      ContractorPerformance performance) {
    return ContractorPerformanceModel(
      contractorId: performance.contractorId,
      averageRating: performance.averageRating,
      totalJobs: performance.totalJobs,
      completedJobs: performance.completedJobs,
      activeJobs: performance.activeJobs,
      averageCompletionTime: performance.averageCompletionTime,
      onTimePercentage: performance.onTimePercentage,
      totalRevenue: performance.totalRevenue,
    );
  }

  ContractorPerformance toEntity() => this;
}

/// Contractor rating model for JSON serialization
class ContractorRatingModel extends ContractorRating {
  const ContractorRatingModel({
    required super.id,
    required super.contractorId,
    required super.workOrderId,
    required super.rating,
    required super.qualityRating,
    required super.communicationRating,
    required super.timelinessRating,
    super.review,
    super.reviewerName,
    required super.createdAt,
  });

  factory ContractorRatingModel.fromJson(Map<String, dynamic> json) {
    return ContractorRatingModel(
      id: json['id']?.toString() ?? '',
      contractorId: json['contractor_id']?.toString() ?? '',
      workOrderId: json['work_order_id']?.toString() ?? '',
      rating: json['rating'] as int? ?? 0,
      qualityRating: json['quality_rating'] as int? ?? 0,
      communicationRating: json['communication_rating'] as int? ?? 0,
      timelinessRating: json['timeliness_rating'] as int? ?? 0,
      review: json['review'] as String?,
      reviewerName: json['reviewer_name'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'contractor_id': contractorId,
      'work_order_id': workOrderId,
      'rating': rating,
      'quality_rating': qualityRating,
      'communication_rating': communicationRating,
      'timeliness_rating': timelinessRating,
      if (review != null) 'review': review,
      if (reviewerName != null) 'reviewer_name': reviewerName,
      'created_at': createdAt.toIso8601String(),
    };
  }

  factory ContractorRatingModel.fromEntity(ContractorRating rating) {
    return ContractorRatingModel(
      id: rating.id,
      contractorId: rating.contractorId,
      workOrderId: rating.workOrderId,
      rating: rating.rating,
      qualityRating: rating.qualityRating,
      communicationRating: rating.communicationRating,
      timelinessRating: rating.timelinessRating,
      review: rating.review,
      reviewerName: rating.reviewerName,
      createdAt: rating.createdAt,
    );
  }

  ContractorRating toEntity() => this;
}

/// Contractor statistics model
class ContractorStatsModel {
  final int totalContractors;
  final int activeContractors;
  final int availableContractors;
  final double averageRating;
  final int totalActiveJobs;

  const ContractorStatsModel({
    required this.totalContractors,
    required this.activeContractors,
    required this.availableContractors,
    required this.averageRating,
    required this.totalActiveJobs,
  });

  factory ContractorStatsModel.fromJson(Map<String, dynamic> json) {
    return ContractorStatsModel(
      totalContractors: json['total_contractors'] as int? ?? 0,
      activeContractors: json['active_contractors'] as int? ?? 0,
      availableContractors: json['available_contractors'] as int? ?? 0,
      averageRating: (json['average_rating'] as num?)?.toDouble() ?? 0.0,
      totalActiveJobs: json['total_active_jobs'] as int? ?? 0,
    );
  }

  factory ContractorStatsModel.fromContractors(List<Contractor> contractors) {
    final active =
        contractors.where((c) => c.status == ContractorStatus.active).length;
    final available = contractors.where((c) => c.isAvailable).length;
    final totalActiveJobs =
        contractors.fold(0, (sum, c) => sum + c.activeJobs);
    final avgRating = contractors.isNotEmpty
        ? contractors.fold(0.0, (sum, c) => sum + c.rating) /
            contractors.length
        : 0.0;

    return ContractorStatsModel(
      totalContractors: contractors.length,
      activeContractors: active,
      availableContractors: available,
      averageRating: avgRating,
      totalActiveJobs: totalActiveJobs,
    );
  }
}
