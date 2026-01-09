# Backend Dockerfile for FastAPI application
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and README for dependencies
COPY pyproject.toml ./
COPY README.md ./

# Copy application code (needed for editable install)
COPY medicare_agent ./medicare_agent
COPY main.py ./
COPY scripts ./scripts

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copy data directories (indexes and documents)
# Note: These should be mounted as volumes in production
COPY data ./data
COPY docs ./docs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application
CMD ["python", "main.py"]
