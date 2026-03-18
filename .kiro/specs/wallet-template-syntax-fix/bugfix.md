# Bugfix Requirements Document

## Introduction

The wallet overview template contains an invalid Django template filter syntax on line 134. The `floatformat` filter is being called with multiple arguments in an unsupported format: `{{ w.amount|floatformat:isSelectedCrypto:8 }}`. This causes a TemplateSyntaxError when accessing the wallet page at `/wallet/`, preventing users from viewing their wallet overview and pending withdrawals.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the wallet overview page is accessed at `/wallet/` THEN the system raises a TemplateSyntaxError due to invalid filter syntax in the template

1.2 WHEN the template attempts to render a pending withdrawal amount with `{{ w.amount|floatformat:isSelectedCrypto:8 }}` THEN the system fails to parse the filter because `floatformat` does not accept multiple colon-separated arguments

### Expected Behavior (Correct)

2.1 WHEN the wallet overview page is accessed at `/wallet/` THEN the system SHALL render the page without errors

2.2 WHEN the template renders a pending withdrawal amount THEN the system SHALL display the amount formatted with the appropriate decimal places without syntax errors

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the wallet overview page displays other formatted amounts like `{{ wallet.get_total_balance_usd|floatformat:2 }}` THEN the system SHALL CONTINUE TO render them correctly

3.2 WHEN the wallet overview page displays recent transactions with `{{ tx.amount|floatformat:8 }}` THEN the system SHALL CONTINUE TO render them correctly

3.3 WHEN the wallet overview page displays the primary currency selector THEN the system SHALL CONTINUE TO function without changes
