# Wallet Template Syntax Fix - Design Document

## Overview

The wallet overview template contains an invalid Django template filter syntax on line 134 that prevents the page from rendering. The `floatformat` filter is being called with multiple colon-separated arguments (`{{ w.amount|floatformat:isSelectedCrypto:8 }}`), but Django's `floatformat` filter only accepts a single argument for decimal places. This causes a TemplateSyntaxError when accessing the wallet page, blocking users from viewing their wallet overview and pending withdrawals. The fix involves replacing the invalid syntax with a valid approach that properly formats withdrawal amounts with the correct number of decimal places.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when the wallet overview template attempts to render a pending withdrawal amount using invalid `floatformat` filter syntax with multiple arguments
- **Property (P)**: The desired behavior when rendering pending withdrawal amounts - amounts should display with proper decimal formatting without syntax errors
- **Preservation**: Existing formatting for other amounts in the template (total balance, recent transactions) that must remain unchanged by the fix
- **floatformat filter**: Django's built-in template filter that formats decimal numbers to a specified number of decimal places
- **pending_withdrawals**: The list of WithdrawalRequest objects passed to the template context, each containing an `amount` field (DecimalField with max_digits=18, decimal_places=8)
- **isSelectedCrypto**: A variable that appears to be intended to control decimal places dynamically, but is not passed to the template context

## Bug Details

### Bug Condition

The bug manifests when the wallet overview page is accessed at `/wallet/`. The template attempts to render pending withdrawal amounts using `{{ w.amount|floatformat:isSelectedCrypto:8 }}` on line 134. Django's `floatformat` filter does not accept multiple colon-separated arguments in this format. The filter syntax is invalid because:

1. `floatformat` only accepts a single argument (the number of decimal places)
2. The syntax `floatformat:isSelectedCrypto:8` attempts to pass two arguments, which is not supported
3. `isSelectedCrypto` is not defined in the template context and would cause a variable resolution error even if the syntax were valid

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type TemplateRenderRequest
  OUTPUT: boolean
  
  RETURN input.template_path == "wallet/overview.html"
         AND input.context_contains("pending_withdrawals")
         AND template_contains_invalid_filter_syntax(input.template, "floatformat:isSelectedCrypto:8")
END FUNCTION
```

### Examples

- **Example 1 - Current Defect**: When accessing `/wallet/`, the template engine encounters `{{ w.amount|floatformat:isSelectedCrypto:8 }}` and raises `TemplateSyntaxError: Could not parse the remainder: ':isSelectedCrypto:8' from 'w.amount|floatformat:isSelectedCrypto:8'`
- **Example 2 - Expected Behavior**: When accessing `/wallet/`, the template renders successfully and displays pending withdrawal amounts formatted with 8 decimal places (e.g., "0.12345678 BTC")
- **Example 3 - Edge Case**: A pending withdrawal with amount `Decimal('0.00000001')` should display as "0.00000001" without truncation
- **Example 4 - Edge Case**: A pending withdrawal with amount `Decimal('1.5')` should display as "1.50000000" with trailing zeros to match 8 decimal places

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- The total balance display `{{ wallet.get_total_balance_usd|floatformat:2 }}` must continue to render correctly with 2 decimal places
- Recent transaction amounts `{{ tx.amount|floatformat:8 }}` must continue to render correctly with 8 decimal places
- The primary currency selector and all other UI elements must remain unchanged
- The page layout, styling, and all other template logic must remain unaffected

**Scope:**
All other template rendering and functionality should be completely unaffected by this fix. This includes:
- All other `floatformat` filter usages in the template
- All other template tags and filters
- The view logic and context data passed to the template
- The styling and layout of the page

## Hypothesized Root Cause

Based on the bug description and code analysis, the most likely issues are:

1. **Incorrect Filter Syntax**: The developer attempted to pass multiple arguments to `floatformat` using colon-separated syntax, which is not supported by Django's `floatformat` filter. The filter only accepts a single integer argument for decimal places.

2. **Undefined Variable**: The variable `isSelectedCrypto` is not passed to the template context in the `wallet_overview` view function, so even if the syntax were valid, it would fail to resolve.

3. **Misunderstanding of Filter Capabilities**: The developer may have confused Django's `floatformat` filter with a custom filter that accepts multiple arguments, or may have attempted to use a syntax pattern that doesn't exist in Django templates.

4. **Copy-Paste Error**: The syntax may have been copied from documentation or another source and incorrectly applied, with the assumption that `floatformat` supports variable decimal places through multiple arguments.

## Correctness Properties

Property 1: Bug Condition - Template Renders Without Syntax Error

_For any_ request to the wallet overview page where pending withdrawals exist, the fixed template SHALL render successfully without raising a TemplateSyntaxError, and pending withdrawal amounts SHALL display with proper decimal formatting.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Other Formatting Continues to Work

_For any_ template rendering that does NOT involve the invalid `floatformat:isSelectedCrypto:8` syntax (such as total balance display, recent transaction amounts, and other template elements), the fixed template SHALL produce exactly the same output as the original template, preserving all existing formatting and functionality.

**Validates: Requirements 3.1, 3.2, 3.3**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `apps/wallet/templates/wallet/overview.html`

**Line**: 134

**Current Code**:
```html
<span class="text-sm font-bold text-white">{{ w.currency.code }} {{ w.amount|floatformat:isSelectedCrypto:8 }}</span>
```

**Specific Changes**:

1. **Replace Invalid Filter Syntax**: Replace `{{ w.amount|floatformat:isSelectedCrypto:8 }}` with `{{ w.amount|floatformat:8 }}`
   - Remove the invalid `isSelectedCrypto` argument
   - Keep the valid `8` decimal places argument
   - This will format the withdrawal amount to 8 decimal places, which is appropriate for cryptocurrency amounts

2. **Rationale**: 
   - The `floatformat` filter in Django only accepts a single argument: the number of decimal places
   - Since `WithdrawalRequest.amount` is a DecimalField with `decimal_places=8`, formatting to 8 decimal places is the correct approach
   - The `isSelectedCrypto` variable appears to be unused and is not passed to the template context
   - Using a fixed 8 decimal places is consistent with how cryptocurrency amounts are displayed elsewhere in the template (see line 169: `{{ tx.amount|floatformat:8 }}`)

**Fixed Code**:
```html
<span class="text-sm font-bold text-white">{{ w.currency.code }} {{ w.amount|floatformat:8 }}</span>
```

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that attempt to render the wallet overview template with pending withdrawals on the UNFIXED code. Observe the TemplateSyntaxError and confirm it matches the expected error pattern.

**Test Cases**:
1. **Template Syntax Error Test**: Render the wallet overview template with pending withdrawals and assert that a TemplateSyntaxError is raised (will fail on unfixed code)
2. **Error Message Validation**: Verify the error message contains "floatformat:isSelectedCrypto:8" to confirm the exact location of the syntax error
3. **Page Access Test**: Attempt to access `/wallet/` and verify it returns a 500 error due to template rendering failure (will fail on unfixed code)
4. **Multiple Withdrawals Test**: Render the template with multiple pending withdrawals and verify the error occurs for each one (will fail on unfixed code)

**Expected Counterexamples**:
- TemplateSyntaxError with message containing "Could not parse the remainder: ':isSelectedCrypto:8'"
- HTTP 500 error when accessing the wallet overview page
- Template rendering fails before any HTML is generated

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (template rendering with pending withdrawals), the fixed template produces the expected behavior (successful rendering with properly formatted amounts).

**Pseudocode:**
```
FOR ALL pending_withdrawal IN pending_withdrawals DO
  result := render_template_with_withdrawal(pending_withdrawal)
  ASSERT result.status == "success"
  ASSERT result.html_contains(format_amount(pending_withdrawal.amount, 8))
  ASSERT result.html_does_not_contain("TemplateSyntaxError")
END FOR
```

### Preservation Checking

**Goal**: Verify that for all template rendering that does NOT involve the invalid syntax, the fixed template produces the same result as the original template.

**Pseudocode:**
```
FOR ALL other_template_elements IN template DO
  IF NOT contains_invalid_syntax(other_template_elements) THEN
    ASSERT original_template_output(other_template_elements) = fixed_template_output(other_template_elements)
  END IF
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across different wallet states
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that other formatting continues to work correctly

**Test Plan**: Observe behavior on UNFIXED code first for other formatting (total balance, recent transactions), then write property-based tests capturing that behavior and verifying it continues after the fix.

**Test Cases**:
1. **Total Balance Formatting Preservation**: Verify `{{ wallet.get_total_balance_usd|floatformat:2 }}` continues to display correctly with 2 decimal places
2. **Recent Transaction Formatting Preservation**: Verify `{{ tx.amount|floatformat:8 }}` continues to display correctly with 8 decimal places
3. **Currency Code Display Preservation**: Verify `{{ w.currency.code }}` continues to display correctly
4. **Page Layout Preservation**: Verify the overall page structure and styling remain unchanged

### Unit Tests

- Test that the wallet overview page renders successfully with pending withdrawals
- Test that pending withdrawal amounts display with 8 decimal places
- Test edge cases: very small amounts (0.00000001), large amounts, amounts with trailing zeros
- Test that the page renders correctly when there are no pending withdrawals
- Test that other formatted amounts (total balance, recent transactions) continue to display correctly

### Property-Based Tests

- Generate random pending withdrawal amounts and verify they render with 8 decimal places
- Generate random wallet states with various balances and verify all formatting works correctly
- Test that all template elements render without errors across many different wallet configurations
- Verify that the fix doesn't introduce any new template syntax errors

### Integration Tests

- Test full page load at `/wallet/` with pending withdrawals
- Test page load with multiple pending withdrawals
- Test page load with no pending withdrawals
- Test that clicking on withdrawal details link works correctly
- Test that the page renders correctly in different browsers/contexts
