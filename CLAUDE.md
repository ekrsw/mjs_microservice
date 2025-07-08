# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python microservices architecture project with two main services:
- **auth-service**: Handles user authentication and JWT token management using RS256 algorithm
- **user-service**: Manages user data and operations, receives user events from auth-service

Both services are built with FastAPI and use PostgreSQL databases, Redis for caching (auth-service only), and RabbitMQ for inter-service communication.

## Development Commands

### Running the Application
```bash
# Start all services with Docker Compose
docker-compose up -d

# Start specific service
docker-compose up -d auth-service
docker-compose up -d user-service

# View logs
docker-compose logs -f auth-service
docker-compose logs -f user-service

# Stop services
docker-compose down
```

### Running Tests
```bash
# Run tests for auth-service
cd auth-service
python -m pytest tests/ -v

# Run tests for user-service  
cd user-service
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/unit/crud/test_crud_auth_user_normal.py -v

# Run tests with coverage
python -m pytest tests/ -v --cov=app --cov-report=html
```

### Database Operations
```bash
# Run database migrations for auth-service
cd auth-service
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Run database migrations for user-service
cd user-service
alembic upgrade head

# View migration history
alembic history

# Downgrade to specific revision
alembic downgrade -1
```

### Environment Setup
Both services require a `.env` file with database credentials, Redis settings, and RabbitMQ configuration. Key environment variables include:
- `AUTH_POSTGRES_*` and `USER_POSTGRES_*` for database connections
- `RABBITMQ_*` for message broker settings
- `AUTH_REDIS_*` for Redis configuration (auth-service only)
- JWT token settings: `ALGORITHM`, `PRIVATE_KEY_PATH`, `PUBLIC_KEY_PATH`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`

## Architecture Overview

### Microservices Communication
- **RabbitMQ**: Message broker for asynchronous communication between services
- **Topic Exchange**: Uses `user_events` and `auth_events` exchanges with routing keys
- **Event-Driven**: Services communicate through events (user creation, authentication events)
- **Routing Keys**: auth-service uses `user.sync`, user-service uses `user.created`
- **Message Flow**: auth-service publishes user events → user-service consumes and processes → user-service publishes responses

### Data Layer
- **SQLAlchemy 2.0**: ORM with async support
- **Alembic**: Database migrations
- **PostgreSQL**: Separate databases for each service
- **Redis**: Token blacklisting and caching (auth-service only)

### Security
- **JWT Tokens**: RS256 algorithm with RSA key pairs
- **Token Blacklisting**: Redis-based token revocation
- **Password Hashing**: bcrypt for secure password storage
- **Public/Private Keys**: Located in `keys/` directory for each service

### Service Structure
Each service follows this pattern:
```
app/
├── api/v1/          # API endpoints
├── core/            # Configuration, logging, security
├── crud/            # Database operations
├── db/              # Database setup and sessions
├── messaging/       # RabbitMQ handlers
├── models/          # SQLAlchemy models
└── schemas/         # Pydantic schemas
```

### Key Components
- **FastAPI**: Web framework with automatic OpenAPI docs
- **Dependency Injection**: Database sessions and authentication
- **Logging**: Structured logging with request IDs
- **Health Checks**: `/health` endpoints for monitoring
- **CORS**: Configured for cross-origin requests

### Testing
- **pytest**: Test framework with async support
- **pytest-asyncio**: For async test support
- **In-memory SQLite**: For isolated database tests using `sqlite+aiosqlite:///:memory:`
- **Fixtures**: Reusable test data and database sessions in `conftest.py`
- **Test Structure**: Unit tests organized by component (crud, security, etc.)
- **Test Coverage**: `pytest-cov` for coverage reporting

## Important Notes

### Token Management
- Private keys are used for signing JWT tokens (auth-service)
- Public keys are shared with other services for verification
- Token blacklisting is implemented via Redis

### Database Sessions
- Async sessions with proper error handling and rollback
- Connection pooling and health checks configured
- Separate databases per service for isolation

### Message Handling
- RabbitMQ consumers set up during application startup
- Event handlers for user creation and authentication events
- Robust error handling and retry logic

### Docker Configuration
- Multi-stage builds for production optimization
- Health checks for all services (PostgreSQL, RabbitMQ)
- Resource limits and network isolation (separate networks per service)
- Volume mounts for development (hot-reload)
- Service dependencies managed with `depends_on` and health checks

### Network Architecture
- **auth-network**: Isolated network for auth-service and its dependencies
- **user-network**: Isolated network for user-service and its dependencies  
- **microservice-network**: Shared network for RabbitMQ communication
- Services communicate through RabbitMQ on the shared network