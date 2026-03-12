# Implementation Plan: Payment System Integration

## Overview

This implementation plan breaks down the payment system integration into incremental, testable steps. Each task builds on previous work, ensuring the system remains functional throughout development. The implementation follows the provider abstraction pattern, implements comprehensive security measures, and includes both unit and property-based tests.

## Tasks

- [x] 1. Set up provider SDK foundation
  - Create `apps/payments/providers/__init__.py` with provider registry
  - Create `apps/payments/providers/base.py` with BasePaymentProvider abstract class
  - Define dataclasses: DepositResponse, PayoutResponse, StatusResponse
  - Implement `get_provider_instance()` factory function
  - Create custom exception: ProviderAPIError
  - _Requirements: 3.1, 3.4, 3.8_

- [x] 1.1 Write property test for provider response standardization
  - **Property 18: Provider response standardization**
  - **Validates: Requirements 3.4**

- [x] 2. Implement RUkassa provider
  - [x] 2.1 Create `apps/payments/providers/rukassa.py` with RUkassaProvider class
    - Implement `create_deposit()` method with API call to RUkassa
    - Implement `check_deposit_status()` method
    - Implement `create_payout()` method
    - Implement `check_payout_status()` method
    - Implement `verify_webhook_signature()` with MD5 verification
    - Implement `parse_webhook()` method
    - Implement `_map_status()` for status mapping
    - Implement `_generate_signature()` helper
    - Implement `_make_request()` with timeout handling (30 seconds)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.10_
  
  - [x] 2.2 Write property test for RUkassa signature verification
    - **Property 14: RUkassa signature verification**
    - **Validates: Requirements 1.5, 6.5**
  
  - [ ]* 2.3 Write property test for status mapping
    - **Property 21: Status mapping completeness**
    - **Validates: Requirements 3.7**
  
  - [ ]* 2.4 Write unit tests for RUkassa provider
    - Test create_deposit with valid parameters
    - Test API timeout handling (edge case)
    - Test error response handling
    - _Requirements: 1.3, 1.10_

- [x] 3. Implement NOWpayments provider
  - [x] 3.1 Create `apps/payments/providers/nowpayments.py` with NOWpaymentsProvider class
    - Implement `create_deposit()` with auto-conversion support
    - Implement `check_deposit_status()` method
    - Implement `create_payout()` method
    - Implement `check_payout_status()` method
    - Implement `verify_webhook_signature()` with HMAC SHA-512
    - Implement `parse_webhook()` method
    - Implement `_map_status()` for status mapping
    - Implement `_make_request()` with timeout handling
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.10_
  
  - [ ]* 3.2 Write property test for NOWpayments signature verification
    - **Property 15: NOWpayments signature verification**
    - **Validates: Requirements 2.5, 6.6**
  
  - [ ]* 3.3 Write property test for partial payment tracking
    - **Property 41: Partial payment tracking**
    - **Validates: Requirements 2.7, 13.5**
  
  - [ ]* 3.4 Write unit tests for NOWpayments provider
    - Test create_deposit with auto-conversion
    - Test partial payment handling
    - Test API timeout handling (edge case)
    - _Requirements: 2.2, 2.7, 2.10_

- [x] 4. Checkpoint - Ensure provider SDK tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Payment Service
  - [x] 5.1 Create `apps/payments/services/payment_service.py` with PaymentService class
    - Implement `create_deposit()` method with validation and fraud checks
    - Implement `process_webhook_confirmation()` with idempotency
    - Implement `check_pending_deposits()` background task method
    - Implement `expire_old_deposits()` background task method
    - Implement `_calculate_fee()` helper
    - Implement `_build_success_url()`, `_build_fail_url()`, `_build_webhook_url()` helpers
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10_
  
  - [ ]* 5.2 Write property test for deposit idempotency
    - **Property 1: Deposit idempotency**
    - **Validates: Requirements 4.9, 6.9**
  
  - [ ]* 5.3 Write property test for deposit order uniqueness
    - **Property 2: Deposit order uniqueness**
    - **Validates: Requirements 4.2**
  
  - [ ]* 5.4 Write property test for deposit expiration timing
    - **Property 3: Deposit expiration timing**
    - **Validates: Requirements 4.3**
  
  - [ ]* 5.5 Write property test for deposit atomic crediting
    - **Property 4: Deposit atomic crediting**
    - **Validates: Requirements 4.5, 4.6**
  
  - [ ]* 5.6 Write property test for deposit amount validation
    - **Property 5: Deposit amount validation**
    - **Validates: Requirements 4.1**
  
  - [ ]* 5.7 Write unit tests for Payment Service
    - Test successful deposit creation
    - Test webhook processing with completed status
    - Test expired deposit marking
    - _Requirements: 4.2, 4.5, 4.8_

- [x] 6. Implement Payout Service
  - [x] 6.1 Create `apps/payments/services/payout_service.py` with PayoutService class
    - Implement `create_payout()` method
    - Implement `_initiate_payout()` helper
    - Implement `process_webhook_confirmation()` method
    - Implement `retry_failed_payouts()` background task method
    - Implement `_select_provider()` helper
    - Implement `_get_payment_method()` helper
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10_
  
  - [ ]* 6.2 Write property test for payout retry logic
    - **Property 8: Payout retry logic**
    - **Validates: Requirements 5.8, 9.4**
  
  - [ ]* 6.3 Write property test for payout terminal failure
    - **Property 9: Payout terminal failure**
    - **Validates: Requirements 5.9**
  
  - [ ]* 6.4 Write property test for payout-withdrawal consistency
    - **Property 10: Payout-withdrawal consistency**
    - **Validates: Requirements 5.10**
  
  - [ ]* 6.5 Write unit tests for Payout Service
    - Test successful payout creation
    - Test retry logic with exponential backoff
    - Test terminal failure after max retries
    - _Requirements: 5.4, 5.8, 5.9_

- [x] 7. Checkpoint - Ensure service layer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement Webhook Handler
  - [x] 8.1 Create `apps/payments/webhooks/handler.py` with WebhookHandler class
    - Implement `handle_deposit_webhook()` view method
    - Implement `handle_payout_webhook()` view method
    - Implement `_verify_ip()` with IP whitelist checking
    - Implement `_extract_signature()` helper
    - Implement `_get_client_ip()` helper
    - Add IP_WHITELISTS configuration for RUkassa and NOWpayments
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10_
  
  - [ ]* 8.2 Write property test for webhook logging completeness
    - **Property 12: Webhook logging completeness**
    - **Validates: Requirements 6.1**
  
  - [ ]* 8.3 Write property test for IP whitelist enforcement
    - **Property 13: IP whitelist enforcement**
    - **Validates: Requirements 6.2, 6.3**
  
  - [ ]* 8.4 Write property test for invalid signature rejection
    - **Property 16: Invalid signature rejection**
    - **Validates: Requirements 6.7**
  
  - [ ]* 8.5 Write unit tests for Webhook Handler
    - Test webhook with valid signature
    - Test webhook with invalid signature (rejected)
    - Test webhook from non-whitelisted IP (rejected)
    - Test duplicate webhook (idempotency)
    - _Requirements: 6.3, 6.7, 6.9_

- [x] 9. Implement Anti-Fraud Service
  - [x] 9.1 Create `apps/payments/services/anti_fraud_service.py` with AntiFraudService class
    - Implement `check_deposit()` method with all fraud checks
    - Implement `check_withdrawal()` method (delegates to existing WithdrawalRequest.calculate_risk_level)
    - Implement `_notify_admins_large_deposit()` helper
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9_
  
  - [ ]* 9.2 Write property test for daily deposit limit enforcement
    - **Property 25: Daily deposit limit enforcement**
    - **Validates: Requirements 7.1**
  
  - [ ]* 9.3 Write property test for large deposit notification
    - **Property 26: Large deposit notification**
    - **Validates: Requirements 7.2**
  
  - [ ]* 9.4 Write property test for multiple IP flagging
    - **Property 27: Multiple IP flagging**
    - **Validates: Requirements 7.3**
  
  - [ ]* 9.5 Write unit tests for Anti-Fraud Service
    - Test daily limit blocking
    - Test large deposit notification
    - Test multiple IP detection
    - Test no-bet withdrawal risk increase
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 10. Implement Saved Payment Methods
  - [x] 10.1 Add methods to SavedPaymentMethod model
    - Add `mask_card_number()` static method
    - Add `encrypt_details()` method
    - Add `decrypt_details()` method
    - Update `save()` method to auto-encrypt sensitive fields
    - _Requirements: 8.2, 8.3, 8.4, 8.9, 8.10_
  
  - [ ]* 10.2 Write property test for card number masking
    - **Property 31: Card number masking**
    - **Validates: Requirements 8.3, 11.3**
  
  - [ ]* 10.3 Write property test for payment details encryption
    - **Property 35: Payment details encryption**
    - **Validates: Requirements 8.10, 11.2**
  
  - [ ]* 10.4 Write unit tests for Saved Payment Methods
    - Test card masking (only last 4 digits stored)
    - Test crypto address storage (full address)
    - Test encryption/decryption round trip
    - Test soft deletion
    - _Requirements: 8.3, 8.4, 8.8, 8.10_

- [x] 11. Implement Fee Calculation
  - [x] 11.1 Add fee calculation methods to PaymentService
    - Update `_calculate_fee()` to apply fee_fixed first, then fee_percent
    - Add `calculate_deposit_total()` method for UI display
    - Add `calculate_withdrawal_net()` method for UI display
    - _Requirements: 13.1, 13.2, 13.3, 13.7, 13.9, 13.10_
  
  - [ ]* 11.2 Write property test for fee calculation order
    - **Property 36: Fee calculation order**
    - **Validates: Requirements 13.7**
  
  - [ ]* 11.3 Write property test for decimal places formatting
    - **Property 40: Decimal places formatting**
    - **Validates: Requirements 13.10**
  
  - [ ]* 11.4 Write unit tests for fee calculations
    - Test fee calculation with various amounts
    - Test conversion fee application
    - Test decimal places formatting for different currencies
    - _Requirements: 13.2, 13.3, 13.7, 13.9, 13.10_

- [x] 12. Checkpoint - Ensure core logic tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Implement Celery background tasks
  - [x] 13.1 Create `apps/payments/tasks.py` with Celery tasks
    - Implement `check_pending_deposits` task (calls PaymentService method)
    - Implement `check_pending_payouts` task (calls PayoutService method)
    - Implement `expire_old_deposits` task
    - Implement `retry_failed_payouts` task
    - Implement `generate_daily_reports` task
    - Implement `provider_health_checks` task
    - Implement `reconciliation_check` task
    - Implement `cleanup_old_webhook_logs` task
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10_
  
  - [x] 13.2 Update `config/celery.py` with beat schedule
    - Add all task schedules as specified in design
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10_
  
  - [ ]* 13.3 Write unit tests for background tasks
    - Test check_pending_deposits finds and updates orders
    - Test expire_old_deposits marks expired orders
    - Test retry_failed_payouts with backoff
    - Test cleanup_old_webhook_logs deletes old records
    - _Requirements: 9.1, 9.3, 9.4, 9.10_

- [x] 14. Implement deposit views and templates
  - [x] 14.1 Create deposit views in `apps/payments/views.py`
    - Implement `deposit_page` view (list providers and methods)
    - Implement `create_deposit` view (calls PaymentService.create_deposit)
    - Implement `deposit_status` view (check order status)
    - Implement `deposit_success` view
    - Implement `deposit_failure` view
    - _Requirements: 14.1, 14.2, 14.3, 14.6, 14.7_
  
  - [x] 14.2 Create deposit templates
    - Create `templates/payments/deposit.html` (provider selection)
    - Create `templates/payments/deposit_crypto.html` (crypto payment page with QR code)
    - Create `templates/payments/deposit_success.html`
    - Create `templates/payments/deposit_failure.html`
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.6, 14.7_
  
  - [ ]* 14.3 Write unit tests for deposit views
    - Test deposit page renders providers
    - Test create_deposit creates order and redirects
    - Test deposit_success displays transaction details
    - _Requirements: 14.1, 14.2, 14.6_

- [x] 15. Implement withdrawal views and templates
  - [x] 15.1 Create withdrawal views in `apps/payments/views.py`
    - Implement `withdrawal_page` view (show saved methods and form)
    - Implement `create_withdrawal` view (creates WithdrawalRequest, then calls PayoutService)
    - Implement `withdrawal_status` view
    - _Requirements: 14.8, 14.9_
  
  - [x] 15.2 Create withdrawal templates
    - Create `templates/payments/withdrawal.html` (saved methods and form)
    - Update existing withdrawal templates if needed
    - _Requirements: 14.8, 14.9_
  
  - [ ]* 15.3 Write unit tests for withdrawal views
    - Test withdrawal page displays saved methods
    - Test create_withdrawal validates amount and creates payout
    - _Requirements: 14.8, 5.1_

- [x] 16. Implement transaction history view
  - [x] 16.1 Create transaction history view
    - Implement `transaction_history` view (list deposits and withdrawals)
    - Create `templates/payments/transaction_history.html`
    - _Requirements: 14.10_
  
  - [ ]* 16.2 Write unit test for transaction history
    - Test page displays user's deposits and withdrawals
    - _Requirements: 14.10_

- [x] 17. Implement URL routing
  - [x] 17.1 Create `apps/payments/urls.py`
    - Add URL patterns for all views
    - Add webhook URL patterns
    - _Requirements: All view requirements_
  
  - [x] 17.2 Update `config/urls.py`
    - Include payments URLs
    - Include webhook URLs at root level
    - _Requirements: All view requirements_

- [-] 18. Checkpoint - Ensure views and templates work
  - Ensure all tests pass, ask the user if questions arise.

- [~] 19. Implement Admin Interface
  - [ ] 19.1 Update `apps/payments/admin.py`
    - Customize PaymentProviderAdmin (list display, filters, actions)
    - Customize PaymentMethodAdmin
    - Customize DepositOrderAdmin (filters, search, actions for manual completion)
    - Customize PayoutOrderAdmin (filters, search, actions for manual approval)
    - Customize WebhookLogAdmin (filters, search, readonly fields)
    - Customize SavedPaymentMethodAdmin
    - Customize PaymentSettingsAdmin
    - Add payment dashboard with statistics
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 10.10_
  
  - [ ]* 19.2 Write unit tests for admin actions
    - Test manual deposit completion action
    - Test manual payout approval action
    - Test provider enable/disable action
    - _Requirements: 10.7, 10.8, 10.2_

- [~] 20. Implement Security Features
  - [ ] 20.1 Add rate limiting middleware
    - Create `apps/payments/middleware.py` with RateLimitMiddleware
    - Implement rate limiting for deposit/withdrawal endpoints (10/min, 5/min)
    - _Requirements: 11.7_
  
  - [ ] 20.2 Add log redaction utility
    - Create `apps/payments/utils/log_redaction.py`
    - Implement `redact_sensitive_data()` function
    - Update all logging calls to use redaction
    - _Requirements: 11.6_
  
  - [ ] 20.3 Add 2FA enforcement for withdrawals
    - Update withdrawal view to check user.two_factor_enabled
    - Require 2FA verification before processing withdrawal
    - _Requirements: 11.8_
  
  - [ ]* 20.4 Write property test for rate limiting
    - **Property 45: Rate limiting enforcement**
    - **Validates: Requirements 11.7**
  
  - [ ]* 20.5 Write property test for log redaction
    - **Property 44: Log data redaction**
    - **Validates: Requirements 11.6**
  
  - [ ]* 20.6 Write unit tests for security features
    - Test rate limiting blocks excessive requests
    - Test log redaction removes sensitive data
    - Test 2FA enforcement for withdrawals
    - _Requirements: 11.7, 11.6, 11.8_

- [~] 21. Implement Error Handling and Circuit Breaker
  - [ ] 21.1 Create circuit breaker utility
    - Create `apps/payments/utils/circuit_breaker.py`
    - Implement CircuitBreaker class with open/half-open/closed states
    - _Requirements: 12.7, 12.8, 12.9_
  
  - [ ] 21.2 Integrate circuit breaker into provider SDK
    - Update BasePaymentProvider._make_request() to use circuit breaker
    - Implement retry logic with exponential backoff
    - _Requirements: 12.5, 12.6, 12.7_
  
  - [ ]* 21.3 Write property test for circuit breaker
    - **Property 50: Circuit breaker opening**
    - **Property 51: Circuit breaker cached response**
    - **Property 52: Circuit breaker auto-recovery**
    - **Validates: Requirements 12.7, 12.8, 12.9**
  
  - [ ]* 21.4 Write unit tests for error handling
    - Test retry logic with exponential backoff
    - Test circuit breaker opens after 5 failures
    - Test circuit breaker returns cached response when open
    - Test circuit breaker closes after recovery
    - _Requirements: 12.5, 12.7, 12.8, 12.9_

- [~] 22. Checkpoint - Ensure security and error handling tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [~] 23. Add environment configuration
  - [ ] 23.1 Update `.env.example` with payment provider variables
    - Add RUkassa configuration variables
    - Add NOWpayments configuration variables
    - Add payment settings variables
    - _Requirements: 11.1_
  
  - [ ] 23.2 Create configuration documentation
    - Document all environment variables
    - Document provider setup instructions
    - _Requirements: 11.1_

- [~] 24. Add monitoring and metrics
  - [ ] 24.1 Create Prometheus metrics
    - Create `apps/payments/metrics.py`
    - Add counters for deposits, payouts, webhooks
    - Add histograms for amounts and processing times
    - Add gauges for provider health
    - _Requirements: 16.8_
  
  - [ ] 24.2 Update views and services to record metrics
    - Add metric recording to PaymentService
    - Add metric recording to PayoutService
    - Add metric recording to WebhookHandler
    - _Requirements: 16.8_

- [~] 25. Integration testing
  - [ ]* 25.1 Write integration tests for complete deposit flow
    - Test end-to-end deposit with RUkassa (sandbox)
    - Test end-to-end deposit with NOWpayments (sandbox)
    - Test webhook processing updates order and credits wallet
    - _Requirements: 1.1-1.7, 2.1-2.8, 4.1-4.10_
  
  - [ ]* 25.2 Write integration tests for complete payout flow
    - Test end-to-end payout with RUkassa (sandbox)
    - Test end-to-end payout with NOWpayments (sandbox)
    - Test webhook processing completes payout
    - _Requirements: 5.1-5.10_
  
  - [ ]* 25.3 Write integration tests for fraud detection
    - Test daily limit enforcement blocks deposits
    - Test high-risk withdrawal requires manual approval
    - _Requirements: 7.1, 7.6_

- [~] 26. Final checkpoint - Complete system test
  - Run all tests (unit, property, integration)
  - Verify all requirements are covered
  - Test in sandbox environments
  - Ensure all tests pass, ask the user if questions arise.

- [~] 27. Documentation and deployment preparation
  - [ ] 27.1 Create deployment checklist
    - Document environment variable setup
    - Document database migration steps (none needed)
    - Document Celery configuration
    - Document webhook URL configuration
    - Document monitoring setup
    - _Requirements: All_
  
  - [ ] 27.2 Create operational runbook
    - Document common issues and solutions
    - Document manual intervention procedures
    - Document provider contact information
    - _Requirements: All_
  
  - [ ] 27.3 Create user documentation
    - Document deposit process for users
    - Document withdrawal process for users
    - Document supported payment methods
    - _Requirements: 14.1-14.10_

## Notes

- Tasks marked with `*` are optional test tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties (minimum 100 iterations each)
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows with provider sandboxes
- The implementation uses Python/Django as specified in the design
- All provider API credentials must be stored in environment variables
- Webhook endpoints must have IP whitelisting enabled before production
- Test mode should be used during development (provider sandboxes)
