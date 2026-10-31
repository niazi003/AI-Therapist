# Personal Wellbeing Companion - Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml ./

# Install dependencies using pip
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.32.0" \
    "pydantic>=2.10.0" \
    "pydantic-settings>=2.6.0" \
    "groq>=0.11.0" \
    "httpx>=0.27.0" \
    "sqlalchemy[asyncio]>=2.0.36" \
    "greenlet>=3.0.0" \
    "alembic>=1.14.0" \
    "psycopg2-binary>=2.9.10" \
    "asyncpg>=0.30.0" \
    "python-jose[cryptography]>=3.3.0" \
    "bcrypt>=4.1.0" \
    "python-multipart>=0.0.17" \
    "langgraph>=0.2.0" \
    "langgraph-checkpoint-postgres>=3.2.0" \
    "psycopg[binary,pool]>=3.3.6" \
    "pycountry>=24.6.1" \
    "email-validator>=2.0.0"

# Copy application code
COPY app/ ./app/
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY startup.py ./

# Expose port
EXPOSE 8000

# Run the application with database initialization
CMD ["python", "startup.py"]