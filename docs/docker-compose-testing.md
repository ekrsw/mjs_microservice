# Docker Compose Testing Guide

This document explains how to run tests using Docker Compose from the project root directory.

## Overview

The project provides a containerized testing environment that allows you to run tests for each microservice in isolated Docker containers. This ensures consistent test environments and eliminates dependency issues.

## Test Commands

### Run All Service Tests

```bash
# Run auth-service tests
docker-compose -f docker-compose.test.yml --profile test run --rm auth-service-test

# Run user-service tests (when available)
docker-compose -f docker-compose.test.yml --profile test run --rm user-service-test
```

### Test with Coverage

```bash
# Auth-service with coverage
docker-compose -f docker-compose.test.yml --profile test run --rm \
  --entrypoint "python -m pytest tests/ -v --cov=app --cov-report=term-missing" \
  auth-service-test
```

### Run Specific Tests

```bash
# Run specific test file
docker-compose -f docker-compose.test.yml --profile test run --rm \
  --entrypoint "python -m pytest tests/unit/crud/test_crud_auth_user_normal.py -v" \
  auth-service-test

# Run specific test function
docker-compose -f docker-compose.test.yml --profile test run --rm \
  --entrypoint "python -m pytest tests/unit/crud/test_crud_auth_user_normal.py::test_create_auth_user -v" \
  auth-service-test
```

## Configuration

### Test Configuration Files

#### docker-compose.test.yml
```yaml
# Test-specific compose file with:
# - Isolated test containers
# - Test profiles for conditional service startup
# - Optimized test Dockerfiles
```

#### auth-service/docker/Dockerfile.test
```dockerfile
# Specialized Dockerfile for testing:
# - No application startup
# - Direct pytest execution
# - Isolated environment variables
```

### Environment Variables

The test environment uses the same environment variables as development but with test-specific overrides:

- Uses SQLite in-memory databases for isolation
- No external database dependencies
- Simplified configuration for testing

## Test Results

### Expected Output

```
========================= test session starts =========================
platform linux -- Python 3.12.9, pytest-8.3.5, pluggy-1.6.0
collecting ... collected 50 items

tests/unit/crud/test_crud_auth_user_edge_cases.py::test_create_multiple_users_transaction_rollback PASSED [  2%]
...
tests/unit/security/test_security.py::test_revoke_refresh_token PASSED [100%]

======================== 50 passed, 1 warning in 14.34s ========================
```

### Success Criteria

- ✅ **All 50 tests pass** for auth-service
- ✅ **No failures or errors**
- ✅ **Fast execution** (under 15 seconds)
- ✅ **Isolated environment** (no external dependencies)

## Architecture

### Test Container Features

1. **Isolation**: Each service has its own test container
2. **Dependencies**: No external database or message broker required
3. **Consistency**: Same environment across all development machines
4. **Speed**: In-memory databases for fast test execution

### Service Structure

```
mjs_microservice/
├── docker-compose.test.yml          # Test orchestration
├── auth-service/
│   ├── docker/
│   │   └── Dockerfile.test          # Test-specific Dockerfile
│   ├── tests/                       # Test files
│   └── conftest.py                  # Test configuration
└── user-service/
    ├── docker/
    │   └── Dockerfile.test          # Test-specific Dockerfile
    └── tests/                       # Test files
```

## Advantages of Docker Testing

### Development Benefits

1. **Consistency**: Same test environment for all developers
2. **Isolation**: No conflicts with local development setup
3. **Clean State**: Fresh environment for each test run
4. **Dependencies**: All required packages bundled in container

### CI/CD Benefits

1. **Reproducible**: Identical environment in CI and local development
2. **Portable**: Runs on any Docker-enabled system
3. **Scalable**: Easy to add new services and tests
4. **Reliable**: No external dependency failures

## Troubleshooting

### Common Issues

#### Build Errors
```bash
# Force rebuild if dependencies change
docker-compose -f docker-compose.test.yml build --no-cache auth-service-test
```

#### Container Cleanup
```bash
# Remove test containers and volumes
docker-compose -f docker-compose.test.yml --profile test down --volumes --remove-orphans

# Remove all test images
docker images --filter=reference="mjs_microservice-*-test" -q | xargs docker rmi
```

#### Environment Variable Issues
```bash
# Check environment variables in container
docker-compose -f docker-compose.test.yml --profile test run --rm \
  --entrypoint "env" auth-service-test
```

### Performance Tips

1. **Parallel Testing**: Run different services in parallel
2. **Volume Caching**: Docker will cache layers for faster rebuilds
3. **Selective Testing**: Use specific test commands for faster feedback

## Development Workflow

### Recommended Testing Flow

```bash
# 1. Quick test during development
cd auth-service
python -m pytest tests/unit/crud/test_crud_auth_user_normal.py::test_create_auth_user -v

# 2. Full service test before commit
docker-compose -f docker-compose.test.yml --profile test run --rm auth-service-test

# 3. Coverage check before release
docker-compose -f docker-compose.test.yml --profile test run --rm \
  --entrypoint "python -m pytest tests/ -v --cov=app --cov-report=html" \
  auth-service-test
```

### Integration with Git Hooks

```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "Running tests..."
docker-compose -f docker-compose.test.yml --profile test run --rm auth-service-test
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

## Future Enhancements

### Planned Features

1. **User-service Testing**: Complete user-service test setup
2. **Integration Tests**: Cross-service testing capabilities
3. **Performance Testing**: Load testing containers
4. **Test Reports**: HTML coverage reports with volume mounts

### CI/CD Integration

```yaml
# GitHub Actions example
name: Test Services
on: [push, pull_request]
jobs:
  test-auth-service:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test auth-service
        run: |
          docker-compose -f docker-compose.test.yml --profile test run --rm auth-service-test
```

This Docker Compose testing setup provides a robust, scalable, and maintainable testing environment for the microservices architecture.