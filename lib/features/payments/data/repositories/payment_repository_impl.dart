import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:somni_property/core/error/failures.dart';
import 'package:somni_property/core/network/api_client.dart';
import 'package:somni_property/features/payments/data/datasources/payment_remote_datasource.dart';
import 'package:somni_property/features/payments/data/models/payment_model.dart';
import 'package:somni_property/features/payments/domain/entities/payment.dart';
import 'package:somni_property/features/payments/domain/repositories/payment_repository.dart';

/// Provider for payment repository
final paymentRepositoryProvider = Provider<PaymentRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final dataSource = PaymentRemoteDataSourceImpl(apiClient);
  return PaymentRepositoryImpl(dataSource);
});

/// Implementation of PaymentRepository
class PaymentRepositoryImpl implements PaymentRepository {
  final PaymentRemoteDataSource _dataSource;

  PaymentRepositoryImpl(this._dataSource);

  @override
  Future<Either<Failure, List<Payment>>> getPayments({
    String? leaseId,
    String? tenantId,
    String? unitId,
    PaymentStatus? status,
    PaymentType? type,
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    try {
      final payments = await _dataSource.getPayments(
        leaseId: leaseId,
        tenantId: tenantId,
        unitId: unitId,
        status: status,
        type: type,
        fromDate: fromDate,
        toDate: toDate,
      );
      return Right(payments.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Payment>> getPayment(String id) async {
    try {
      final payment = await _dataSource.getPayment(id);
      return Right(payment.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Payment>>> getPaymentsByStatus(
      PaymentStatus status) async {
    try {
      final payments = await _dataSource.getPaymentsByStatus(status);
      return Right(payments.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Payment>>> getOverduePayments() async {
    try {
      final payments = await _dataSource.getOverduePayments();
      return Right(payments.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Payment>>> getUpcomingPayments(
      int withinDays) async {
    try {
      final payments = await _dataSource.getUpcomingPayments(withinDays);
      return Right(payments.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Payment>>> getPaymentsForLease(
      String leaseId) async {
    try {
      final payments = await _dataSource.getPaymentsForLease(leaseId);
      return Right(payments.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Payment>>> getPaymentsForTenant(
      String tenantId) async {
    try {
      final payments = await _dataSource.getPaymentsForTenant(tenantId);
      return Right(payments.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, PaymentStats>> getPaymentStats({
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    try {
      final stats = await _dataSource.getPaymentStats(
        fromDate: fromDate,
        toDate: toDate,
      );
      return Right(PaymentStats(
        totalPayments: stats.totalPayments,
        pendingPayments: stats.pendingPayments,
        paidPayments: stats.paidPayments,
        overduePayments: stats.overduePayments,
        totalAmountDue: stats.totalAmountDue,
        totalAmountPaid: stats.totalAmountPaid,
        totalOverdue: stats.totalOverdue,
        collectionRate: stats.collectionRate,
      ));
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Payment>> createPayment(Payment payment) async {
    try {
      final model = PaymentModel.fromEntity(payment);
      final created = await _dataSource.createPayment(model);
      return Right(created.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Payment>> updatePayment(Payment payment) async {
    try {
      final model = PaymentModel.fromEntity(payment);
      final updated = await _dataSource.updatePayment(model);
      return Right(updated.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Payment>> recordPayment(
    String paymentId,
    DateTime paidDate,
    PaymentMethod method,
    String? transactionId,
  ) async {
    try {
      final updated = await _dataSource.recordPayment(
        paymentId,
        paidDate,
        method,
        transactionId,
      );
      return Right(updated.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Payment>> applyLateFee(
    String paymentId,
    double lateFeeAmount,
  ) async {
    try {
      final updated = await _dataSource.applyLateFee(paymentId, lateFeeAmount);
      return Right(updated.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Payment>> cancelPayment(
      String paymentId, String reason) async {
    try {
      final updated = await _dataSource.cancelPayment(paymentId, reason);
      return Right(updated.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Payment>> refundPayment(
      String paymentId, String reason) async {
    try {
      final updated = await _dataSource.refundPayment(paymentId, reason);
      return Right(updated.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> deletePayment(String id) async {
    try {
      await _dataSource.deletePayment(id);
      return const Right(null);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Payment>>> generateMonthlyPayments(
    int month,
    int year,
  ) async {
    try {
      final payments = await _dataSource.generateMonthlyPayments(month, year);
      return Right(payments.map((m) => m.toEntity()).toList());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Map<String, dynamic>>> createStripePaymentIntent(
    String paymentId,
    double amount,
    String currency,
  ) async {
    try {
      final result = await _dataSource.createStripePaymentIntent(
        paymentId,
        amount,
        currency,
      );
      return Right(result);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Payment>> processStripePayment(
    String paymentId,
    String paymentIntentId,
  ) async {
    try {
      final payment = await _dataSource.processStripePayment(
        paymentId,
        paymentIntentId,
      );
      return Right(payment.toEntity());
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, String>> getPaymentReceipt(String paymentId) async {
    try {
      final receiptUrl = await _dataSource.getPaymentReceipt(paymentId);
      return Right(receiptUrl);
    } on DioException catch (e) {
      return Left(_handleDioError(e));
    } catch (e) {
      return Left(ServerFailure(message: e.toString()));
    }
  }

  Failure _handleDioError(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return const NetworkFailure(message: 'Connection timeout');
      case DioExceptionType.connectionError:
        return const NetworkFailure(message: 'No internet connection');
      case DioExceptionType.badResponse:
        final statusCode = e.response?.statusCode;
        final message = e.response?.data?['message']?.toString() ??
            e.response?.data?['error']?.toString() ??
            'Server error';
        if (statusCode == 401) {
          return AuthFailure(message: message);
        } else if (statusCode == 404) {
          return NotFoundFailure(message: message);
        } else if (statusCode == 422) {
          return ValidationFailure(message: message);
        }
        return ServerFailure(message: message);
      default:
        return ServerFailure(message: e.message ?? 'Unknown error');
    }
  }
}
