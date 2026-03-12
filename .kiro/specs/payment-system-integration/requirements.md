# Requirements Document: Payment System Integration

## Introduction

This document specifies the requirements for integrating real payment systems into the DOD platform (Stage 3). The system will replace demo deposits with actual payment processing through RUkassa (fiat payments) and NOWpayments (cryptocurrency payments). The integration must support deposits and withdrawals with comprehensive security, fraud detection, webhook handling, and administrative controls.

## Glossary

- **Payment_System**: The complete payment integration subsystem handling deposits and withdrawals
- **RUkassa_Provider**: Payment provider for fiat currencies (cards, SBP, e-wallets, mobile payments)
- **NOWpayments_Provider**: Payment provider for cryptocurrency payments
- **Deposit_Order**: A user-initiated request to add funds to their wallet
- **Payout_Order**: A system-initiated transfer of funds to fulfill a withdrawal request
- **Webhook**: HTTP callback from payment provider notifying status changes
- **Webhook_Handler**: Service that receives, validates, and processes webhooks
- **Payment_Service**: Core service managing deposit lifecycle
- **Payout_Service**: Core service managing withdrawal/payout lifecycle
- **Anti_Fraud_Service**: Service detecting suspicious payment patterns
- **Provider_SDK**: Abstract interface and implementations for payment provider APIs
- **Saved_Payment_Method**: User's stored payment details for faster transactions
- **Payment_Settings**: Global configuration singleton for payment system behavior
- **Idempotency**: Property ensuring duplicate webhook processing doesn't duplicate credits
- **Signature_Verification**: Cryptographic validation of webhook authenticity
- **IP_Whitelist**: List of allowed IP addresses for webhook endpoints
- **Background_Task**: Asynchronous job executed by Celery
- **Reconciliation**: Process of verifying payment records match provider records

## Requirements

### Requirement 1: RUkassa Provider Integration

**User Story:** As a user, I want to deposit funds using Russian payment methods, so that I can fund my wallet with rubles and other regional currencies.

#### Acceptance Criteria

1. WHEN a user selects RUkassa as payment provider, THE Payment_System SHALL display available payment methods (bank cards, SBP, QIWI, ЮMoney, mobile payments)
2. WHEN a user initiates a deposit through RUkassa, THE Payment_System SHALL create a Deposit_Order with status "created"
3. WHEN creating a RUkassa deposit, THE RUkassa_Provider SHALL call the RUkassa API to generate a payment URL
4. WHEN the RUkassa API returns a payment URL, THE Payment_System SHALL redirect the user to that URL
5. WHEN a RUkassa webhook is received, THE Webhook_Handler SHALL verify the MD5 signature using the webhook secret
6. WHEN a RUkassa webhook signature is valid, THE Webhook_Handler SHALL update the Deposit_Order status based on the provider status
7. WHEN a RUkassa deposit is confirmed, THE Payment_Service SHALL credit the user's wallet and create a Transaction record
8. THE RUkassa_Provider SHALL support currencies: RUB, UAH, KZT, UZS, BYN
9. THE RUkassa_Provider SHALL store API credentials in environment variables, not in code
10. WHEN RUkassa API calls timeout after 30 seconds, THE RUkassa_Provider SHALL return an error status

### Requirement 2: NOWpayments Provider Integration

**User Story:** As a user, I want to deposit funds using cryptocurrency, so that I can fund my wallet with Bitcoin, Ethereum, USDT, TON, and other cryptocurrencies.

#### Acceptance Criteria

1. WHEN a user selects NOWpayments as payment provider, THE Payment_System SHALL display available cryptocurrencies (BTC, ETH, USDT, TON, and 200+ others)
2. WHEN a user initiates a crypto deposit, THE NOWpayments_Provider SHALL create a payment with auto-conversion to stablecoins if configured
3. WHEN creating a NOWpayments deposit, THE NOWpayments_Provider SHALL call the NOWpayments API to generate a crypto address
4. WHEN the NOWpayments API returns payment details, THE Payment_System SHALL display the crypto address, QR code, and amount
5. WHEN a NOWpayments webhook is received, THE Webhook_Handler SHALL verify the HMAC SHA-512 signature
6. WHEN a NOWpayments webhook signature is valid, THE Webhook_Handler SHALL update the Deposit_Order status
7. WHEN a crypto deposit is partially paid, THE Payment_System SHALL track the amount_received separately from the requested amount
8. WHEN a crypto deposit is confirmed on the blockchain, THE Payment_Service SHALL credit the user's wallet
9. THE NOWpayments_Provider SHALL store API credentials in environment variables, not in code
10. WHEN NOWpayments API calls timeout after 30 seconds, THE NOWpayments_Provider SHALL return an error status

### Requirement 3: Provider SDK Architecture

**User Story:** As a developer, I want a unified interface for payment providers, so that adding new providers is straightforward and consistent.

#### Acceptance Criteria

1. THE Provider_SDK SHALL define a BasePaymentProvider abstract class with methods: create_deposit, check_deposit_status, create_payout, check_payout_status, verify_webhook_signature, parse_webhook
2. THE RUkassa_Provider SHALL implement BasePaymentProvider interface
3. THE NOWpayments_Provider SHALL implement BasePaymentProvider interface
4. WHEN calling create_deposit, THE Provider_SDK SHALL return a standardized response containing payment_url or crypto_address
5. WHEN calling verify_webhook_signature, THE Provider_SDK SHALL return True if signature is valid, False otherwise
6. WHEN calling parse_webhook, THE Provider_SDK SHALL return a standardized dictionary with order_id, status, amount, and provider_specific_data
7. THE Provider_SDK SHALL map provider-specific statuses to internal statuses (created, pending, processing, completed, failed, expired, cancelled, refunded)
8. WHEN a provider API call fails, THE Provider_SDK SHALL raise a ProviderAPIError exception with error details
9. THE Provider_SDK SHALL log all API requests and responses for debugging
10. THE Provider_SDK SHALL handle rate limiting by implementing exponential backoff

### Requirement 4: Deposit Flow

**User Story:** As a user, I want to deposit funds into my wallet, so that I can use the platform's services.

#### Acceptance Criteria

1. WHEN a user initiates a deposit, THE Payment_Service SHALL validate the amount against min_deposit and max_deposit limits
2. WHEN creating a deposit, THE Payment_Service SHALL create a Deposit_Order record with unique order_id
3. WHEN creating a deposit, THE Payment_Service SHALL set expires_at to 30 minutes from creation
4. WHEN a deposit is created, THE Payment_Service SHALL call the appropriate Provider_SDK to generate payment details
5. WHEN a deposit webhook confirms payment, THE Payment_Service SHALL atomically credit the wallet and update the Deposit_Order status to "completed"
6. WHEN crediting a wallet, THE Payment_Service SHALL create a Transaction record with type "deposit"
7. WHEN a deposit is completed, THE Payment_Service SHALL set completed_at timestamp
8. WHEN a deposit expires without payment, THE Background_Task SHALL update status to "expired"
9. WHEN processing a deposit webhook, THE Payment_Service SHALL ensure idempotency by checking if the order is already completed
10. WHEN a deposit fails, THE Payment_Service SHALL update status to "failed" and log the error

### Requirement 5: Withdrawal Flow

**User Story:** As a user, I want to withdraw funds from my wallet, so that I can receive my winnings in my preferred payment method.

#### Acceptance Criteria

1. WHEN a user requests a withdrawal, THE Payout_Service SHALL validate the amount against min_withdrawal and available balance
2. WHEN creating a withdrawal, THE Payout_Service SHALL create a WithdrawalRequest record (existing model)
3. WHEN a WithdrawalRequest is approved, THE Payout_Service SHALL create a Payout_Order record
4. WHEN creating a payout, THE Payout_Service SHALL call the appropriate Provider_SDK to initiate the transfer
5. WHEN a payout is initiated, THE Payout_Service SHALL update Payout_Order status to "processing"
6. WHEN a payout webhook confirms completion, THE Payout_Service SHALL update status to "completed" and set completed_at
7. WHEN a payout fails, THE Payout_Service SHALL update status to "failed" and increment retry_count
8. WHEN retry_count is less than max_retries, THE Background_Task SHALL retry the payout after exponential backoff delay
9. WHEN retry_count reaches max_retries, THE Payout_Service SHALL mark the payout as permanently failed and notify administrators
10. WHEN a payout is completed, THE Payout_Service SHALL update the WithdrawalRequest status to "completed"

### Requirement 6: Webhook Security

**User Story:** As a system administrator, I want webhooks to be secure and validated, so that malicious actors cannot forge payment confirmations.

#### Acceptance Criteria

1. WHEN a webhook is received, THE Webhook_Handler SHALL create a WebhookLog record with all request details
2. WHEN a webhook is received, THE Webhook_Handler SHALL verify the source IP against the provider's IP whitelist
3. IF the webhook IP is not whitelisted, THEN THE Webhook_Handler SHALL reject the request with HTTP 403
4. WHEN a webhook is received, THE Webhook_Handler SHALL extract the signature from headers or payload
5. WHEN verifying a RUkassa webhook, THE Webhook_Handler SHALL compute MD5 hash and compare with provided signature
6. WHEN verifying a NOWpayments webhook, THE Webhook_Handler SHALL compute HMAC SHA-512 and compare with provided signature
7. IF the webhook signature is invalid, THEN THE Webhook_Handler SHALL reject the request with HTTP 401 and log the attempt
8. WHEN a webhook signature is valid, THE Webhook_Handler SHALL set is_valid_signature to True in WebhookLog
9. WHEN processing a webhook, THE Webhook_Handler SHALL ensure idempotency by checking if the order has already been processed
10. WHEN a webhook is successfully processed, THE Webhook_Handler SHALL set is_processed to True and return HTTP 200

### Requirement 7: Anti-Fraud Detection

**User Story:** As a system administrator, I want to detect and prevent fraudulent deposits and withdrawals, so that the platform is protected from financial losses.

#### Acceptance Criteria

1. WHEN a deposit is created, THE Anti_Fraud_Service SHALL check if the user has exceeded daily_deposit_limit_per_user
2. WHEN a deposit amount is above deposit_notification_threshold, THE Anti_Fraud_Service SHALL notify administrators
3. WHEN a user makes multiple deposits from different IP addresses within 1 hour, THE Anti_Fraud_Service SHALL flag the account for review
4. WHEN a user attempts withdrawal immediately after deposit without placing bets, THE Anti_Fraud_Service SHALL increase the withdrawal risk_level
5. WHEN detecting suspicious patterns, THE Anti_Fraud_Service SHALL add risk_factors to the WithdrawalRequest
6. WHEN a withdrawal has risk_level "high" or "critical", THE Anti_Fraud_Service SHALL require manual approval
7. WHEN a user's account is flagged for fraud, THE Anti_Fraud_Service SHALL freeze the wallet and notify administrators
8. THE Anti_Fraud_Service SHALL track velocity of deposits (number and total amount per time period)
9. WHEN a deposit uses a payment method previously associated with fraud, THE Anti_Fraud_Service SHALL flag the transaction
10. THE Anti_Fraud_Service SHALL maintain a blacklist of payment details (card BINs, crypto addresses) associated with fraud

### Requirement 8: Saved Payment Methods

**User Story:** As a user, I want to save my payment methods, so that I can make faster deposits and withdrawals in the future.

#### Acceptance Criteria

1. WHEN a user completes a successful deposit, THE Payment_System SHALL offer to save the payment method
2. WHEN saving a payment method, THE Payment_System SHALL create a SavedPaymentMethod record
3. WHEN saving a card, THE Payment_System SHALL store only the last 4 digits and card type, never the full number
4. WHEN saving a crypto wallet, THE Payment_System SHALL store the full address
5. WHEN a user has multiple saved payment methods, THE Payment_System SHALL allow marking one as default
6. WHEN a user initiates a deposit, THE Payment_System SHALL display saved payment methods for quick selection
7. WHEN a user selects a saved payment method, THE Payment_System SHALL pre-fill payment details
8. WHEN a user deletes a saved payment method, THE Payment_System SHALL soft-delete the record (keep for audit)
9. WHEN a saved payment method is used, THE Payment_System SHALL update last_used_at timestamp
10. THE Payment_System SHALL encrypt sensitive payment details in SavedPaymentMethod records

### Requirement 9: Background Tasks

**User Story:** As a system administrator, I want automated background tasks to handle payment monitoring and maintenance, so that the system operates reliably without manual intervention.

#### Acceptance Criteria

1. THE Background_Task SHALL check pending deposits every 5 minutes and query provider APIs for status updates
2. THE Background_Task SHALL check pending payouts every 5 minutes and query provider APIs for status updates
3. THE Background_Task SHALL expire deposits older than expires_at with status "pending" or "created"
4. THE Background_Task SHALL retry failed payouts with exponential backoff (1 min, 5 min, 15 min)
5. THE Background_Task SHALL generate daily payment reports with total deposits, withdrawals, fees, and provider breakdown
6. THE Background_Task SHALL perform provider health checks every 15 minutes by calling API status endpoints
7. WHEN a provider health check fails, THE Background_Task SHALL notify administrators and disable the provider
8. THE Background_Task SHALL perform daily reconciliation comparing internal records with provider transaction reports
9. WHEN reconciliation finds discrepancies, THE Background_Task SHALL create alerts for manual review
10. THE Background_Task SHALL clean up expired WebhookLog records older than 90 days

### Requirement 10: Admin Interface

**User Story:** As an administrator, I want to manage payment providers and monitor transactions, so that I can ensure smooth payment operations.

#### Acceptance Criteria

1. THE Admin_Interface SHALL display a list of all PaymentProvider records with status indicators
2. THE Admin_Interface SHALL allow enabling/disabling payment providers and methods
3. THE Admin_Interface SHALL display a dashboard with payment statistics (total deposits, withdrawals, success rates, average processing time)
4. THE Admin_Interface SHALL allow viewing and filtering Deposit_Order records by status, provider, user, date range
5. THE Admin_Interface SHALL allow viewing and filtering Payout_Order records by status, provider, user, date range
6. THE Admin_Interface SHALL display WebhookLog records with filtering by provider, status, date range
7. THE Admin_Interface SHALL allow manually approving or rejecting pending payouts
8. THE Admin_Interface SHALL allow manually completing or failing stuck deposits
9. THE Admin_Interface SHALL display provider API credentials with masked values (show only last 4 characters)
10. THE Admin_Interface SHALL allow updating PaymentSettings configuration values

### Requirement 11: Security and Encryption

**User Story:** As a system administrator, I want sensitive payment data to be encrypted and secured, so that user financial information is protected.

#### Acceptance Criteria

1. THE Payment_System SHALL store all API keys and secrets in environment variables, not in database or code
2. WHEN storing payment details in SavedPaymentMethod, THE Payment_System SHALL encrypt sensitive fields using AES-256
3. WHEN storing card numbers, THE Payment_System SHALL store only masked versions (e.g., "****1234")
4. THE Payment_System SHALL use HTTPS for all API communications with payment providers
5. THE Payment_System SHALL validate SSL certificates when making API requests
6. WHEN logging payment data, THE Payment_System SHALL redact sensitive fields (card numbers, API keys, secrets)
7. THE Payment_System SHALL implement rate limiting on deposit and withdrawal endpoints (10 requests per minute per user)
8. WHEN a user requests withdrawal, THE Payment_System SHALL require 2FA verification if enabled
9. THE Payment_System SHALL log all payment-related actions with user_id, ip_address, and timestamp for audit trail
10. THE Payment_System SHALL implement CSRF protection on all payment forms

### Requirement 12: Error Handling and Resilience

**User Story:** As a user, I want clear error messages when payments fail, so that I understand what went wrong and how to fix it.

#### Acceptance Criteria

1. WHEN a provider API call fails, THE Payment_System SHALL return a user-friendly error message
2. WHEN a deposit fails due to insufficient funds, THE Payment_System SHALL display "Insufficient funds in your payment method"
3. WHEN a deposit fails due to provider error, THE Payment_System SHALL display "Payment provider temporarily unavailable, please try again"
4. WHEN a withdrawal fails due to invalid payment details, THE Payment_System SHALL display "Invalid payment details, please check and try again"
5. WHEN a provider API is unreachable, THE Payment_System SHALL retry the request up to 3 times with exponential backoff
6. WHEN all retries fail, THE Payment_System SHALL log the error and notify administrators
7. THE Payment_System SHALL implement circuit breaker pattern for provider API calls (open circuit after 5 consecutive failures)
8. WHEN a circuit is open, THE Payment_System SHALL return cached error response without calling the provider
9. THE Payment_System SHALL automatically close the circuit after 5 minutes if provider becomes available
10. WHEN a database transaction fails during payment processing, THE Payment_System SHALL rollback all changes and return error

### Requirement 13: Currency Conversion and Fees

**User Story:** As a user, I want to see accurate fees and conversion rates, so that I know exactly how much I will receive or pay.

#### Acceptance Criteria

1. WHEN displaying deposit options, THE Payment_System SHALL show the fee_percent and fee_fixed for each payment method
2. WHEN a user enters a deposit amount, THE Payment_System SHALL calculate and display the total amount including fees
3. WHEN a user enters a withdrawal amount, THE Payment_System SHALL calculate and display the net amount after fees
4. WHEN processing a crypto deposit with auto-conversion, THE Payment_System SHALL track the exchange_rate used
5. WHEN a deposit is completed, THE Payment_System SHALL store the actual amount_received if different from requested amount
6. THE Payment_System SHALL update Currency exchange rates every 15 minutes from external API
7. WHEN calculating fees, THE Payment_System SHALL apply fee_fixed first, then fee_percent to the remaining amount
8. WHEN a user deposits in a currency different from their wallet primary_currency, THE Payment_System SHALL offer automatic conversion
9. WHEN converting currencies, THE Payment_System SHALL apply the conversion_fee_percent from Currency model
10. THE Payment_System SHALL display all amounts with correct decimal_places based on Currency configuration

### Requirement 14: User Interface Updates

**User Story:** As a user, I want an intuitive interface for deposits and withdrawals, so that I can easily manage my funds.

#### Acceptance Criteria

1. WHEN a user visits the deposit page, THE Payment_System SHALL display available payment providers grouped by type (fiat, crypto)
2. WHEN a user selects a payment provider, THE Payment_System SHALL display available payment methods with icons and descriptions
3. WHEN a user selects a payment method, THE Payment_System SHALL display min_amount, max_amount, and processing_time
4. WHEN a user initiates a crypto deposit, THE Payment_System SHALL display a page with crypto address, QR code, amount, and countdown timer
5. WHEN a crypto deposit page is open, THE Payment_System SHALL poll the server every 10 seconds for status updates
6. WHEN a deposit is completed, THE Payment_System SHALL redirect to success page with transaction details
7. WHEN a deposit fails, THE Payment_System SHALL redirect to failure page with error message and retry option
8. WHEN a user visits the withdrawal page, THE Payment_System SHALL display saved payment methods and option to add new
9. WHEN a user selects a withdrawal method, THE Payment_System SHALL display estimated processing time and fees
10. THE Payment_System SHALL display a transaction history page showing all deposits and withdrawals with status indicators

### Requirement 15: Compliance and Reporting

**User Story:** As a compliance officer, I want comprehensive payment reports and audit trails, so that I can ensure regulatory compliance.

#### Acceptance Criteria

1. THE Payment_System SHALL generate daily reports with total deposits, withdrawals, fees collected, and net revenue
2. THE Payment_System SHALL generate monthly reports grouped by payment provider and currency
3. THE Payment_System SHALL maintain an audit log of all payment status changes with timestamp and reason
4. WHEN a payment is manually modified by an administrator, THE Payment_System SHALL log the admin user_id and reason
5. THE Payment_System SHALL generate reports of high-value transactions (above configurable threshold)
6. THE Payment_System SHALL generate reports of failed transactions with error analysis
7. THE Payment_System SHALL export payment data in CSV format for external analysis
8. THE Payment_System SHALL track and report on payment success rates by provider and method
9. THE Payment_System SHALL generate reconciliation reports comparing internal records with provider statements
10. THE Payment_System SHALL retain all payment records and logs for minimum 7 years for compliance

### Requirement 16: Testing and Monitoring

**User Story:** As a developer, I want comprehensive testing and monitoring, so that I can ensure payment system reliability.

#### Acceptance Criteria

1. THE Payment_System SHALL provide a test mode using provider sandbox environments
2. WHEN test mode is enabled, THE Payment_System SHALL use test API credentials and mark all transactions as test
3. THE Payment_System SHALL log all provider API requests and responses with timing information
4. THE Payment_System SHALL track and alert on payment processing times exceeding 30 seconds
5. THE Payment_System SHALL monitor webhook delivery success rates and alert if below 95%
6. THE Payment_System SHALL track provider API error rates and alert if above 5%
7. THE Payment_System SHALL implement health check endpoints for monitoring systems
8. THE Payment_System SHALL expose Prometheus metrics for deposits, withdrawals, fees, and processing times
9. THE Payment_System SHALL send alerts to administrators when critical errors occur
10. THE Payment_System SHALL maintain uptime SLA of 99.9% for payment processing
