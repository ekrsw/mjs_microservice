# Auth-Service Testing Guide

This document provides comprehensive testing commands and guidelines for the auth-service.

## Quick Start

```bash
# Navigate to auth-service directory
cd auth-service

# Run all tests
python -m pytest tests/ -v
```

## Test Commands

### Basic Test Execution

#### Run All Tests
```bash
# All tests with verbose output
python -m pytest tests/ -v

# All tests with extra verbose output
python -m pytest tests/ -vv

# All tests with minimal output
python -m pytest tests/
```

#### Run Specific Test Files
```bash
# CRUD tests - Normal operations
python -m pytest tests/unit/crud/test_crud_auth_user_normal.py -v

# CRUD tests - Error handling
python -m pytest tests/unit/crud/test_crud_auth_user_error.py -v

# CRUD tests - Edge cases
python -m pytest tests/unit/crud/test_crud_auth_user_edge_cases.py -v

# Security tests
python -m pytest tests/unit/security/test_security.py -v
```

#### Run Specific Test Functions
```bash
# User creation test
python -m pytest tests/unit/crud/test_crud_auth_user_normal.py::test_create_auth_user -v

# Multiple user creation test
python -m pytest tests/unit/crud/test_crud_auth_user_normal.py::test_create_multiple_auth_users -v

# Password hashing test
python -m pytest tests/unit/security/test_security.py::test_password_hash -v

# JWT token creation test
python -m pytest tests/unit/security/test_security.py::test_create_access_token -v

# Token blacklist test
python -m pytest tests/unit/security/test_security.py::test_blacklist_token -v
```

### Test Coverage

#### Generate Coverage Reports
```bash
# HTML coverage report
python -m pytest tests/ -v --cov=app --cov-report=html

# Terminal coverage report
python -m pytest tests/ -v --cov=app --cov-report=term

# Coverage with missing lines
python -m pytest tests/ -v --cov=app --cov-report=term-missing

# Save coverage to file
python -m pytest tests/ -v --cov=app --cov-report=html:htmlcov
```

#### View Coverage
```bash
# Open HTML coverage report (after generating)
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Test Filtering

#### Filter by Keywords
```bash
# Run tests containing 'create'
python -m pytest tests/ -v -k "create"

# Run tests containing 'password'
python -m pytest tests/ -v -k "password"

# Run tests containing 'error'
python -m pytest tests/ -v -k "error"

# Run tests containing 'update'
python -m pytest tests/ -v -k "update"

# Run tests containing 'delete'
python -m pytest tests/ -v -k "delete"

# Exclude tests containing 'slow'
python -m pytest tests/ -v -k "not slow"
```

#### Filter by Test Patterns
```bash
# Run only CRUD tests
python -m pytest tests/unit/crud/ -v

# Run only security tests
python -m pytest tests/unit/security/ -v

# Run tests matching pattern
python -m pytest tests/ -v -k "test_create_*"
```

### Advanced Options

#### Execution Control
```bash
# Stop on first failure
python -m pytest tests/ -v -x

# Stop after N failures
python -m pytest tests/ -v --maxfail=3

# Run failed tests from last run
python -m pytest tests/ -v --lf

# Run failed tests first, then continue
python -m pytest tests/ -v --ff
```

#### Performance and Debugging
```bash
# Show slowest 10 tests
python -m pytest tests/ -v --durations=10

# Show all test durations
python -m pytest tests/ -v --durations=0

# Capture output (show print statements)
python -m pytest tests/ -v -s

# Disable output capture
python -m pytest tests/ -v --capture=no
```

#### Parallel Execution
```bash
# Run tests in parallel (requires pytest-xdist)
pip install pytest-xdist
python -m pytest tests/ -v -n auto

# Run with specific number of workers
python -m pytest tests/ -v -n 4
```

## Test Structure

### Current Test Organization
```
tests/
├── conftest.py              # Test configuration and fixtures
├── unit/
│   ├── crud/
│   │   ├── test_crud_auth_user_normal.py      # Normal CRUD operations
│   │   ├── test_crud_auth_user_error.py       # Error handling
│   │   └── test_crud_auth_user_edge_cases.py  # Edge cases
│   └── security/
│       └── test_security.py                   # Security functions
```

### Test Categories

#### CRUD Tests (36 tests)
- **Normal Operations**: User creation, retrieval, update, deletion
- **Error Handling**: Duplicate detection, validation errors
- **Edge Cases**: Transaction rollback, database errors

#### Security Tests (14 tests)
- **Password Management**: Hashing, verification
- **JWT Tokens**: Creation, verification, expiration
- **Token Blacklisting**: Blacklist management, verification
- **Refresh Tokens**: Creation, verification, revocation

### Test Fixtures

#### Database Fixtures
```python
# Available fixtures in conftest.py
@pytest_asyncio.fixture
async def db_engine():
    """In-memory SQLite database engine"""

@pytest_asyncio.fixture  
async def db_session(db_engine):
    """Database session with automatic rollback"""

@pytest.fixture
def unique_username():
    """Generate unique username for tests"""

@pytest.fixture
def unique_email():
    """Generate unique email for tests"""

@pytest_asyncio.fixture
async def test_user(db_session, unique_username, unique_email):
    """Pre-created test user"""
```

## Test Results

### Expected Output
```
========================= test session starts =========================
collected 50 items

tests/unit/crud/test_crud_auth_user_edge_cases.py::test_create_multiple_users_transaction_rollback PASSED [  2%]
tests/unit/crud/test_crud_auth_user_edge_cases.py::test_create_multiple_users_with_duplicate_constraint PASSED [  4%]
...
tests/unit/security/test_security.py::test_revoke_refresh_token PASSED [100%]

======================== 50 passed, 1 warning in 12.80s ========================
```

### Success Criteria
- **All 50 tests pass**
- **No test failures or errors**
- **Warnings are acceptable** (passlib deprecation warning)

## Continuous Integration

### GitHub Actions Example
```yaml
name: Auth Service Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd auth-service
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd auth-service
          python -m pytest tests/ -v --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./auth-service/coverage.xml
```

## Troubleshooting

### Common Issues

#### Missing Environment Variables
```bash
# Error: AUTH_POSTGRES_EXTERNAL_PORT field required
# Solution: Ensure .env file has all required variables
cp .env.example .env
```

#### Database Connection Errors
```bash
# Error: Cannot connect to auth-db
# Solution: Tests should use SQLite, check fixture usage
# Ensure test functions use db_session or db_engine fixtures
```

#### Import Errors
```bash
# Error: ModuleNotFoundError
# Solution: Run tests from auth-service directory
cd auth-service
python -m pytest tests/ -v
```

### Performance Tips

1. **Use specific test selection** for faster feedback during development
2. **Run parallel tests** for full test suite execution
3. **Use coverage selectively** - only when needed for reports
4. **Filter tests by keywords** to focus on specific functionality

## Development Workflow

### Recommended Testing Flow
```bash
# 1. Quick smoke test
python -m pytest tests/unit/crud/test_crud_auth_user_normal.py::test_create_auth_user -v

# 2. Test specific module you're working on
python -m pytest tests/unit/crud/ -v -k "create"

# 3. Run related tests
python -m pytest tests/ -v -k "auth_user"

# 4. Full test suite before commit
python -m pytest tests/ -v

# 5. Coverage check before release
python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

This testing guide ensures comprehensive verification of auth-service functionality and provides efficient workflows for development and CI/CD processes.