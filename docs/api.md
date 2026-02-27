# docs/api.md

## API документация DOD Platform

### Authentication
- POST /accounts/login/ - Login (email, password)
- POST /accounts/signup/ - Register (email, username, password)
- POST /accounts/logout/ - Logout

### Wallet
- GET /wallet/balance/ - Get user balance
- POST /wallet/deposit/ - Create deposit
- POST /wallet/withdraw/ - Create withdrawal
- GET /wallet/transactions/ - List transactions

### Sports Betting
- GET /sports/ - List sports/leagues
- GET /sports/event/<id>/ - Event details
- POST /sports/bet/ - Place bet
- GET /sports/bets/ - User bets

### Casino
- GET /casino/ - List games
- POST /casino/crash/bet/ - Place crash bet
- WebSocket /ws/casino/ - Real-time updates

### Predictions
- GET /predictions/markets/ - List markets
- POST /predictions/trade/ - Buy/sell shares
- GET /predictions/positions/ - User positions

### Support
- POST /support/ticket/ - Create ticket
- GET /support/tickets/ - List tickets

### Admin
- GET /admin-panel/dashboard/ - Dashboard
- POST /admin-panel/user/<id>/block/ - Block user

### Health
- GET /health/ - Health check (DB, Redis, Celery)
