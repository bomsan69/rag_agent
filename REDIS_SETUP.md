# Redis Setup Guide

This document explains how Redis is configured for different environments in the Medicare AI Chatbot.

## 📋 Overview

Redis is used to store conversation history for multi-turn conversations. The setup differs between development and production environments:

- **Development**: Uses external Redis server (localhost)
- **Production/Docker**: Uses containerized Redis in docker-compose

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Development                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Backend (localhost:8000)                          │
│       ↓                                            │
│  External Redis (localhost:6379)                   │
│                                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              Production (Docker)                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐      ┌──────────────┐           │
│  │   Backend    │─────>│    Redis     │           │
│  │ Container    │      │  Container   │           │
│  │ (backend)    │      │  (redis)     │           │
│  └──────────────┘      └──────────────┘           │
│         ↑                                          │
│  ┌──────────────┐                                 │
│  │  Frontend    │                                 │
│  │  Container   │                                 │
│  └──────────────┘                                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 Configuration

### Environment Variables

**`.env` (for local development)**
```bash
# Redis Configuration
REDIS_HOST=localhost          # Local Redis for development
REDIS_PORT=6379
REDIS_PASSWORD=               # Empty for local dev
REDIS_DB=0
CONVERSATION_HISTORY_TTL=1800 # 30 minutes (backup, actual cleanup on session close)
MAX_CONVERSATION_MESSAGES=10  # Keep last 10 messages in context
```

**`docker-compose.yml` (for production)**
```yaml
services:
  redis:
    image: redis:7-alpine
    # ... Redis container config

  backend:
    environment:
      - REDIS_HOST=redis  # Override to use Docker service name
    depends_on:
      redis:
        condition: service_healthy
```

---

## 🚀 Setup Instructions

### Development Environment

**Option 1: Using Homebrew (macOS)**
```bash
# Install Redis
brew install redis

# Start Redis
brew services start redis

# Verify Redis is running
redis-cli ping
# Expected output: PONG
```

**Option 2: Using Docker**
```bash
# Run Redis in Docker (detached)
docker run -d \
  --name medicare-redis \
  -p 6379:6379 \
  redis:7-alpine

# Verify
docker ps | grep redis
redis-cli ping
```

**Option 3: Using apt (Ubuntu/Debian)**
```bash
# Install Redis
sudo apt update
sudo apt install redis-server

# Start Redis
sudo systemctl start redis-server

# Enable auto-start
sudo systemctl enable redis-server

# Verify
redis-cli ping
```

### Production Environment (Docker Compose)

**No additional setup needed!** Redis is automatically included in docker-compose:

```bash
# Build and start all services (including Redis)
docker-compose up --build

# Redis will be available at 'redis:6379' within Docker network
```

---

## 🧪 Testing Redis Connection

### Development
```bash
# Test Redis connection
redis-cli ping

# Check if conversation history is being saved
redis-cli
> KEYS conversation:*
> GET conversation:<session_id>
> TTL conversation:<session_id>
```

### Production (Docker)
```bash
# Connect to Redis container
docker exec -it medicare-agent-redis redis-cli

# Check conversation history
KEYS conversation:*
GET conversation:<session_id>
```

---

## 📊 Data Structure

### Conversation History Format

**Redis Key**: `conversation:<session_id>`

**Value** (JSON array):
```json
[
  {
    "role": "user",
    "content": "When can I enroll in Medicare?",
    "metadata": null
  },
  {
    "role": "assistant",
    "content": "According to the Medicare Handbook...",
    "metadata": {
      "citations": [...],
      "confidence": "high"
    }
  }
]
```

**TTL**: 1800 seconds (30 minutes, but deleted on session close)

---

## 🔍 Monitoring

### Check Redis Memory Usage
```bash
# Development
redis-cli INFO memory

# Docker
docker exec medicare-agent-redis redis-cli INFO memory
```

### Monitor Active Sessions
```bash
# Count active sessions
redis-cli KEYS "conversation:*" | wc -l

# View all session keys
redis-cli KEYS "conversation:*"
```

### View Specific Session
```bash
# Get session data (formatted)
redis-cli GET "conversation:<session_id>" | jq .

# Check TTL
redis-cli TTL "conversation:<session_id>"
```

---

## 🛠️ Troubleshooting

### Problem: Backend can't connect to Redis

**Development**:
```bash
# Check if Redis is running
redis-cli ping

# If not running:
brew services start redis  # macOS
sudo systemctl start redis-server  # Linux
```

**Docker**:
```bash
# Check Redis container status
docker-compose ps redis

# View Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

### Problem: Conversation history not persisting

**Check Redis logs**:
```bash
# Development
tail -f /usr/local/var/log/redis.log  # macOS Homebrew

# Docker
docker-compose logs -f redis
```

**Check backend logs**:
```bash
docker-compose logs -f backend | grep -i redis
```

### Problem: Redis memory usage too high

**Clear all conversation history**:
```bash
# Development
redis-cli FLUSHDB

# Docker
docker exec medicare-agent-redis redis-cli FLUSHDB
```

**Set memory limit** (add to docker-compose.yml):
```yaml
redis:
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

---

## 🔐 Security

### Development
- No password by default (localhost only)
- Not exposed to network

### Production Recommendations

**Add password protection** (docker-compose.yml):
```yaml
redis:
  command: redis-server --appendonly yes --requirepass YOUR_STRONG_PASSWORD
  environment:
    - REDIS_PASSWORD=YOUR_STRONG_PASSWORD
```

**Update .env**:
```bash
REDIS_PASSWORD=YOUR_STRONG_PASSWORD
```

**Bind to specific interface** (production):
```yaml
redis:
  command: redis-server --appendonly yes --bind 127.0.0.1
```

---

## 📈 Performance Tuning

### Optimize for Conversation History

**Recommended Redis Configuration**:
```yaml
redis:
  command: >
    redis-server
    --appendonly yes
    --maxmemory 512mb
    --maxmemory-policy allkeys-lru
    --save ""
    --tcp-keepalive 60
```

**Explanation**:
- `--appendonly yes`: Persist data to disk
- `--maxmemory 512mb`: Limit memory usage
- `--maxmemory-policy allkeys-lru`: Evict oldest keys when memory full
- `--save ""`: Disable RDB snapshots (AOF is enough)
- `--tcp-keepalive 60`: Keep connections alive

---

## 🔄 Data Persistence

### Development
Redis data is stored in:
- macOS (Homebrew): `/usr/local/var/db/redis/`
- Linux: `/var/lib/redis/`

### Docker
Redis data is stored in Docker volume `redis-data`:

```bash
# Inspect volume
docker volume inspect medicare_agent_redis-data

# Backup volume
docker run --rm \
  -v medicare_agent_redis-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/redis-backup.tar.gz /data

# Restore volume
docker run --rm \
  -v medicare_agent_redis-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/redis-backup.tar.gz -C /
```

---

## 🧹 Cleanup

### Remove Old Sessions (Manual)
```bash
# Find sessions older than 1 hour
redis-cli --scan --pattern "conversation:*" | while read key; do
  ttl=$(redis-cli TTL "$key")
  if [ "$ttl" -lt 1800 ]; then
    echo "Deleting old session: $key"
    redis-cli DEL "$key"
  fi
done
```

### Clear All Data
```bash
# Development
redis-cli FLUSHALL

# Docker
docker exec medicare-agent-redis redis-cli FLUSHALL
```

### Remove Docker Volume
```bash
# Stop containers
docker-compose down

# Remove Redis volume (deletes all data)
docker volume rm medicare_agent_redis-data

# Restart
docker-compose up
```

---

## 📚 Additional Resources

- [Redis Documentation](https://redis.io/documentation)
- [Redis Best Practices](https://redis.io/topics/admin)
- [Docker Compose Redis](https://hub.docker.com/_/redis)
- [Python Redis Client](https://redis-py.readthedocs.io/)

---

## ✅ Verification Checklist

**Development Environment**:
- [ ] Redis installed and running
- [ ] `redis-cli ping` returns PONG
- [ ] Backend connects successfully (check logs)
- [ ] Conversation history saved in Redis

**Production Environment**:
- [ ] `docker-compose up` starts all services
- [ ] Redis container healthy: `docker-compose ps redis`
- [ ] Backend connects to Redis: `docker-compose logs backend | grep -i redis`
- [ ] Conversation history works in chat UI
- [ ] Session cleanup on browser close

---

For questions or issues, check the backend logs:
```bash
# Development
tail -f logs/app.log

# Docker
docker-compose logs -f backend
```
