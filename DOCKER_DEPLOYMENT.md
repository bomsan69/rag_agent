# Docker Deployment Guide

This guide explains how to deploy the Medicare AI Chatbot using Docker.

## Prerequisites

- Docker (version 20.10+)
- Docker Compose (version 2.0+)
- At least 4GB of available RAM
- At least 10GB of available disk space

## Quick Start

### 1. Environment Setup

Create `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and set your API keys:

```env
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Tavily Search Configuration
TAVILY_API_KEY=your-tavily-api-key-here
ENABLE_WEB_SEARCH=true
WEB_SEARCH_MAX_RESULTS=5

# Application Configuration
APP_ENV=production
LOG_LEVEL=INFO

# Document Configuration
MEDICARE_DOC_VERSION=2026
MEDICARE_PDF_PATH=./docs/medicare_manual.pdf

# Index Configuration
INDEX_PATH=./data/indexes
CHUNK_SIZE=600
CHUNK_OVERLAP=300
TOP_K_RETRIEVAL=20
TOP_K_RERANK=8

# Performance Optimization
ENABLE_QUERY_EXPANSION=true
ENABLE_INTENT_CLASSIFICATION=true
ENABLE_VERIFICATION=true
SKIP_VERIFICATION_ON_STREAM=true
USE_FAST_MODEL_FOR_CLASSIFICATION=true
FAST_MODEL=gpt-3.5-turbo

# Retrieval Weights
BM25_WEIGHT=0.3
VECTOR_WEIGHT=0.7

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

Create `frontend/.env.local` file:

```bash
cp frontend/.env.local.example frontend/.env.local
```

Edit `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:4000/api/v1
```

**Note**: In production, replace `localhost:4000` with your domain.

### 2. Build and Run

Build and start all services:

```bash
docker-compose up --build
```

Or run in detached mode:

```bash
docker-compose up -d --build
```

### 3. Access the Application

Once the containers are running:

- **Frontend**: http://localhost:4000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## Docker Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

### Stop Services

```bash
docker-compose down
```

### Stop and Remove Volumes

```bash
docker-compose down -v
```

### Rebuild a Specific Service

```bash
# Rebuild backend
docker-compose build backend

# Rebuild frontend
docker-compose build frontend
```

### Restart Services

```bash
docker-compose restart
```

## Production Deployment

### 1. Environment Variables

For production, update the following in `.env`:

```env
APP_ENV=production
LOG_LEVEL=WARNING

# Use production domain
NEXT_PUBLIC_API_BASE_URL=https://yourdomain.com/api/v1
```

### 2. Build Indexes

Before deploying, ensure you have built the search indexes:

```bash
# Run locally or in a container
docker-compose run backend python scripts/build_index.py
```

### 3. Use External Volumes

For production, mount external volumes for data persistence:

```yaml
services:
  backend:
    volumes:
      - /path/to/persistent/data:/app/data
      - /path/to/persistent/docs:/app/docs
```

### 4. Enable HTTPS

Use a reverse proxy like Nginx or Traefik:

**Example Nginx Configuration:**

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:4000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Resource Limits

Add resource constraints to docker-compose.yml:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  frontend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Troubleshooting

### Container Fails to Start

Check logs:
```bash
docker-compose logs backend
```

Common issues:
- Missing API keys in `.env`
- Port conflicts (change ports in docker-compose.yml)
- Insufficient memory

### Frontend Can't Connect to Backend

1. Check backend health:
```bash
curl http://localhost:8000/api/v1/health
```

2. Verify network:
```bash
docker network inspect medicare_agent_medicare-network
```

3. Check environment variables:
```bash
docker-compose exec frontend printenv | grep API
```

### Index Not Found

Build indexes:
```bash
docker-compose run backend python scripts/build_index.py
```

Or copy pre-built indexes to `./data/indexes/`

## Monitoring

### Health Checks

Both services include health checks:

```bash
# Check backend
curl http://localhost:8000/api/v1/health

# Check frontend
curl http://localhost:4000
```

### Container Status

```bash
docker-compose ps
```

## Updating the Application

### Pull Latest Changes

```bash
git pull origin main
docker-compose down
docker-compose up --build -d
```

### Update Dependencies

Backend:
```bash
docker-compose build --no-cache backend
```

Frontend:
```bash
docker-compose build --no-cache frontend
```

## Backup and Restore

### Backup Data

```bash
# Backup indexes
tar -czf indexes-backup.tar.gz ./data/indexes/

# Backup documents
tar -czf docs-backup.tar.gz ./docs/
```

### Restore Data

```bash
# Restore indexes
tar -xzf indexes-backup.tar.gz -C ./

# Restore documents
tar -xzf docs-backup.tar.gz -C ./
```

## Security Considerations

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Use secrets management** in production (Docker secrets, Vault, etc.)
3. **Enable firewall** - Only expose ports 4000 (frontend)
4. **Regular updates** - Keep Docker images and dependencies updated
5. **Scan images** - Use `docker scan` to check for vulnerabilities

```bash
docker scan medicare-agent-backend
docker scan medicare-agent-frontend
```

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review health status: `docker-compose ps`
- Refer to main README.md for application-specific help
