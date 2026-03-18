# Bugfix Requirements Document

## Introduction

The casino game "canada-africa" returns a 404 error when accessed at `/casino/canada-africa/?demo=1`. This bug affects user experience as players cannot access the canada-africa game through the expected URL path. The root cause is that the URL routing configuration does not include a direct route for canada-* games at the expected path format.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user navigates to `/casino/canada-africa/` THEN the system returns HTTP 404 Not Found error
1.2 WHEN a user navigates to `/casino/canada-africa/?demo=1` THEN the system returns HTTP 404 Not Found error
1.3 WHEN a user attempts to access any `canada-*` game using the format `/casino/canada-{game_name}/` THEN the system returns HTTP 404 Not Found error

### Expected Behavior (Correct)

2.1 WHEN a user navigates to `/casino/canada-africa/` THEN the system SHALL render the canada-africa game wrapper page
2.2 WHEN a user navigates to `/casino/canada-africa/?demo=1` THEN the system SHALL render the canada-africa game wrapper page with demo mode enabled
2.3 WHEN a user navigates to `/casino/canada-{game_name}/` for any valid canada-* game THEN the system SHALL render the corresponding game wrapper page

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user navigates to `/casino/game/canada-africa/` THEN the system SHALL CONTINUE TO render the canada-africa game wrapper page (existing route)
3.2 WHEN a user navigates to standard game routes (`/casino/crash/`, `/casino/slots/`, `/casino/roulette/`, `/casino/mines/`, `/casino/dice/`, `/casino/plinko/`) THEN the system SHALL CONTINUE TO render the corresponding game pages
3.3 WHEN a user accesses any `viperpro-*` game using `/casino/game/viperpro-{game_name}/` THEN the system SHALL CONTINUE TO render the corresponding game wrapper page