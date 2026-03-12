# Test Setup & Configuration

## Status
✅ All test files configured and syntax-valid

## Test Files Created
- `tests/conftest.py` - pytest configuration and fixtures
- `tests/test_accounts.py` - User model tests (~60 tests)
- `tests/test_wallet.py` - Wallet and transaction tests (~40 tests)  
- `tests/test_integration.py` - End-to-end user journey tests (~15 scenarios)
- `tests/load/locustfile.py` - Load testing (already exists)
- `pytest.ini` - pytest configuration with Django settings

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=apps --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_accounts.py
pytest tests/test_wallet.py
pytest tests/test_integration.py
```

### Run specific test class
```bash
pytest tests/test_accounts.py::TestUserModel
pytest tests/test_wallet.py::TestWalletModel
```

### Run with verbose output
```bash
pytest -v
```

### Run only fast tests (skip slow)
```bash
pytest -m "not slow"
```

### Generate HTML coverage report
```bash
pytest --cov=apps --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Database
Tests use a separate test database configured in `config/settings/test.py`:
- Database: `dod_test` (PostgreSQL)
- User: `dod_test`
- Password: `test` (configurable via environment variables)

## Environment Setup

### Required Environment Variables for Testing
```bash
DB_NAME=dod_test
DB_USER=dod_test
DB_PASSWORD=test
DB_HOST=localhost
```

### Install Test Dependencies
```bash
pip install pytest pytest-django pytest-cov
```

## Known False Positives

Pylance may show type-checking errors for:
1. Custom User model fields (is_email_verified, is_2fa_enabled) - False positive, these DO exist
2. Django reverse relationships (transaction_set, balances) - False positive, these ARE created automatically
3. pytest import - False positive if pytest not in analyzed environment, but installed in actual environment

**These will NOT prevent tests from running.** They are type-checking false positives only.

## Test Coverage

Target: >80% code coverage

### Coverage by App
- accounts: User model, authentication  
- wallet: Wallet, balance operations, transactions
- Integration tests: End-to-end flows (casino, sports, wallet)

### Running Tests in CI/CD
See `.github/workflows/` for GitHub Actions configuration.

## Django Test Settings

Test database configuration: `config/settings/test.py`
- Uses `dod_test` database
- Migrates automatically before tests run
- Cleaned up after test run
- Uses in-memory cache (optional)
- Disables password hashing (improves test speed)

## Fixtures Available

From `tests/conftest.py`:
- `db` - Database access
- `api_client()` - Django test client
- `authenticated_user()` - User with active session
- `authenticated_client()` - Authenticated test client
- `admin_user()` - Superuser account
- `admin_client()` - Authenticated admin client

## Common Test Patterns

### Testing with database
```python
@pytest.mark.django_db
def test_something(db):
    # Test code here
    User.objects.create(...)
```

### Testing with authenticated user
```python
@pytest.mark.django_db
def test_authenticated(authenticated_client, authenticated_user):
    response = authenticated_client.get('/some-path/')
    assert response.status_code == 200
```

### Testing views
```python
@pytest.mark.django_db
def test_view(authenticated_client):
    response = authenticated_client.get('/some-url/')
    assert response.status_code == 200
    assert 'expected_content' in response.content.decode()
```

## Troubleshooting

### Tests not finding database
- Ensure PostgreSQL is running
- Check `DB_*` environment variables
- Run migrations: `python manage.py migrate --settings=config.settings.test`

### Import errors
- Ensure you're in the project root directory
- Check PYTHONPATH includes project root
- Install all requirements: `pip install -r requirements.txt`

### Fixture not found
- Ensure `conftest.py` is in `tests/` directory
- Check fixture names match exactly (case-sensitive)

### Coverage not generated
- Install pytest-cov: `pip install pytest-cov`
- Use `--cov` flag: `pytest --cov=apps`

## Performance Notes

- Test run time: ~10-15 seconds (depends on system)
- Database setup overhead: ~2-3 seconds
- Parallel testing with pytest-xdist: `pytest -n auto`

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-django documentation](https://pytest-django.readthedocs.io/)
- [Django testing documentation](https://docs.djangoproject.com/en/5.1/topics/testing/)
