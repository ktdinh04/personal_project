# Personal Hub Backend API

FastAPI-based backend for Personal Hub platform.

## Features

- JWT Authentication (access/refresh tokens)
- RBAC (Role-Based Access Control)
- Module/Plugin system loader
- User management
- Audit logging
- MySQL database with Alembic migrations

## Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run development server
uvicorn app.main:app --reload

# Run migrations
alembic upgrade head
```

## API Documentation

When running in development mode, API docs are available at:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
