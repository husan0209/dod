# Implementation Plan

## Bug Condition Exploration Test

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Template Syntax Error on Invalid floatformat Arguments
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For this deterministic bug, scope the property to the concrete failing case: rendering the wallet overview template with pending withdrawals
  - Test implementation details from Bug Condition in design:
    - Render `apps/wallet/templates/wallet/overview.html` with pending_withdrawals context
    - Assert that the template renders successfully WITHOUT raising TemplateSyntaxError
    - Assert that pending withdrawal amounts display with 8 decimal places
    - Assert that the HTML output contains properly formatted amounts (e.g., "0.12345678")
  - The test assertions should match the Expected Behavior Properties from design
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with TemplateSyntaxError (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause:
    - Error message should contain "Could not parse the remainder: ':isSelectedCrypto:8'"
    - This confirms the invalid filter syntax is the root cause
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 2.1, 2.2_

## Preservation Tests

- [~] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Other Template Formatting Continues to Work
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy template elements:
    - Total balance display: `{{ wallet.get_total_balance_usd|floatformat:2 }}` should render with 2 decimal places
    - Recent transaction amounts: `{{ tx.amount|floatformat:8 }}` should render with 8 decimal places
    - Currency codes: `{{ w.currency.code }}` should display correctly
    - Page layout and styling should be intact
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements:
    - Test that total balance formatting with 2 decimal places works correctly
    - Test that recent transaction formatting with 8 decimal places works correctly
    - Test that currency codes display without errors
    - Test that the page structure and layout remain unchanged
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3_

## Implementation

- [~] 3. Fix invalid floatformat filter syntax

  - [ ] 3.1 Implement the fix
    - File: `apps/wallet/templates/wallet/overview.html`
    - Line: 134
    - Current: `{{ w.amount|floatformat:isSelectedCrypto:8 }}`
    - Fixed: `{{ w.amount|floatformat:8 }}`
    - Remove the invalid `isSelectedCrypto` argument from the floatformat filter
    - Keep the 8 decimal places argument for proper cryptocurrency amount formatting
    - Rationale: Django's floatformat filter only accepts a single argument (decimal places). The isSelectedCrypto variable is not passed to template context and the syntax is invalid.
    - _Bug_Condition: isBugCondition(input) where template_contains_invalid_filter_syntax(input.template, "floatformat:isSelectedCrypto:8")_
    - _Expected_Behavior: Template renders successfully without TemplateSyntaxError, pending withdrawal amounts display with 8 decimal places_
    - _Preservation: Total balance formatting (2 decimals), recent transaction formatting (8 decimals), currency codes, and page layout all remain unchanged_
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3_

  - [ ] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Template Renders Successfully with Valid Syntax
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - Verify that:
      - Template renders without TemplateSyntaxError
      - Pending withdrawal amounts display with 8 decimal places
      - HTML output contains properly formatted amounts
    - _Requirements: 2.1, 2.2_

  - [ ] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Other Template Formatting Continues to Work
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix:
      - Total balance formatting with 2 decimal places works correctly
      - Recent transaction formatting with 8 decimal places works correctly
      - Currency codes display without errors
      - Page layout and styling remain unchanged
    - _Requirements: 3.1, 3.2, 3.3_

## Checkpoint

- [~] 4. Checkpoint - Ensure all tests pass
  - Verify all tests pass (exploration test, preservation tests, and any additional unit/integration tests)
  - Confirm the wallet overview page renders successfully at `/wallet/`
  - Confirm pending withdrawals display with proper formatting
  - Confirm no regressions in other template elements
  - Ask the user if questions arise
