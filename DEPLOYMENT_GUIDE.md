# Deployment Guide - AI Stock Advisor (OpenAI Version)

Complete guide for deploying the OpenAI-based agent system to production.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment Options](#production-deployment-options)
4. [Environment Configuration](#environment-configuration)
5. [Security Best Practices](#security-best-practices)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Scaling Considerations](#scaling-considerations)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Python**: 3.9 or higher
- **RAM**: Minimum 4GB, recommended 8GB+
- **Disk Space**: 2GB minimum
- **OS**: Windows, Linux, or macOS

### Required Accounts

1. **OpenAI API Key**
   - Sign up at: https://platform.openai.com/
   - Create API key in dashboard
   - Recommended: Set up billing limits

2. **MCP Server Access** (if using external MCP)
   - Contact your MCP server administrator
   - Get server URL and credentials

---

## Local Development Setup

### Step 1: Clone and Setup

```bash
# Clone repository
git clone <your-repo-url>
cd Final

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

Create `.env` file in project root:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini

# MCP Configuration (if needed)
MCP_SERVER_URL=http://localhost:8000
MCP_API_KEY=your_mcp_api_key

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
```

### Step 3: Run Tests

```bash
# Test full system
python test_full_system_openai.py

# Expected output:
# ==============================================
# FULL SYSTEM TEST SUITE (OpenAI Version)
# ==============================================
# Test 1: MCP Client Connection
# OK - MCP Client connected and working
# ...
# ALL TESTS PASSED - System is working correctly!
```

### Step 4: Run Local UI

```bash
# Option 1: Simple OpenAI UI
streamlit run src/streamlit_ui/app_openai.py

# Option 2: Full Agent System UI (recommended)
streamlit run src/streamlit_ui/app_full_agent.py

# Or use batch scripts:
# Windows:
run_full_agent_ui.bat
# Linux/Mac:
./run_full_agent_ui.sh
```

Access at: http://localhost:8501

---

## Production Deployment Options

### Option 1: Cloud VM Deployment (Recommended)

#### AWS EC2 Deployment

**Step 1: Launch EC2 Instance**

```bash
# Recommended instance: t3.medium or larger
# OS: Ubuntu 22.04 LTS
# Storage: 20GB EBS
# Security Group: Allow ports 22 (SSH), 8501 (Streamlit), 80, 443
```

**Step 2: Setup Server**

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.9 python3-pip python3-venv -y

# Install nginx (for reverse proxy)
sudo apt install nginx -y

# Clone your code
git clone <your-repo-url> /home/ubuntu/ai-stock-advisor
cd /home/ubuntu/ai-stock-advisor

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Step 3: Configure Environment**

```bash
# Create .env file
nano .env

# Add your production keys:
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_MODEL=gpt-4o-mini
DEBUG=false
LOG_LEVEL=WARNING
```

**Step 4: Setup Systemd Service**

Create `/etc/systemd/system/ai-stock-advisor.service`:

```ini
[Unit]
Description=AI Stock Advisor - Streamlit App
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ai-stock-advisor
Environment="PATH=/home/ubuntu/ai-stock-advisor/venv/bin"
ExecStart=/home/ubuntu/ai-stock-advisor/venv/bin/streamlit run src/streamlit_ui/app_full_agent.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

**Step 5: Start Service**

```bash
# Enable and start service
sudo systemctl enable ai-stock-advisor
sudo systemctl start ai-stock-advisor

# Check status
sudo systemctl status ai-stock-advisor

# View logs
sudo journalctl -u ai-stock-advisor -f
```

**Step 6: Configure Nginx Reverse Proxy**

Create `/etc/nginx/sites-available/ai-stock-advisor`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ai-stock-advisor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**Step 7: Setup SSL with Let's Encrypt**

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

---

### Option 2: Docker Deployment

**Step 1: Create Dockerfile**

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8501

# Set environment
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Run app
CMD ["streamlit", "run", "src/streamlit_ui/app_full_agent.py"]
```

**Step 2: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  ai-stock-advisor:
    build: .
    ports:
      - "8501:8501"
    env_file:
      - .env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Step 3: Build and Run**

```bash
# Build image
docker-compose build

# Run container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop container
docker-compose down
```

---

### Option 3: Heroku Deployment

**Step 1: Create Heroku Files**

Create `Procfile`:

```
web: streamlit run src/streamlit_ui/app_full_agent.py --server.port=$PORT --server.address=0.0.0.0
```

Create `setup.sh`:

```bash
#!/bin/bash
mkdir -p ~/.streamlit/
echo "\
[general]\n\
email = \"your-email@example.com\"\n\
" > ~/.streamlit/credentials.toml
echo "\
[server]\n\
headless = true\n\
enableCORS=false\n\
port = $PORT\n\
" > ~/.streamlit/config.toml
```

**Step 2: Deploy to Heroku**

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create your-app-name

# Set config vars
heroku config:set OPENAI_API_KEY=sk-proj-xxxxx
heroku config:set OPENAI_MODEL=gpt-4o-mini

# Deploy
git push heroku main

# Open app
heroku open

# View logs
heroku logs --tail
```

---

## Environment Configuration

### Production .env Template

```env
# ==================== OpenAI Configuration ====================
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini  # or gpt-4o for better quality

# ==================== MCP Configuration ====================
MCP_SERVER_URL=http://your-mcp-server:8000
MCP_API_KEY=your_mcp_api_key
MCP_TIMEOUT=30

# ==================== Application Settings ====================
DEBUG=false
LOG_LEVEL=WARNING  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# ==================== Performance Settings ====================
MAX_WORKERS=4  # Number of concurrent workers
CACHE_TTL=300  # Cache TTL in seconds (5 minutes)
ROUTING_CACHE_ENABLED=true

# ==================== Security Settings ====================
ALLOWED_ORIGINS=https://your-domain.com
API_RATE_LIMIT=100  # Requests per minute
SESSION_TIMEOUT=3600  # Session timeout in seconds (1 hour)

# ==================== Monitoring ====================
ENABLE_METRICS=true
METRICS_PORT=9090
```

---

## Security Best Practices

### 1. API Key Management

**DO:**
- Store API keys in environment variables or secrets manager
- Use separate keys for dev/staging/production
- Set up billing alerts
- Rotate keys regularly
- Use API key restrictions (IP whitelisting, etc.)

**DON'T:**
- Commit API keys to git
- Share API keys between environments
- Use unlimited billing
- Store keys in code

### 2. Access Control

```python
# Add authentication to Streamlit app
# In app_full_agent.py:

import streamlit as st

def check_password():
    """Returns True if user has correct password."""

    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("Password incorrect")
        return False
    else:
        return True

# Add at top of main()
if not check_password():
    st.stop()
```

### 3. Rate Limiting

```python
# Add rate limiting wrapper
from functools import wraps
import time

class RateLimiter:
    def __init__(self, max_calls, time_window):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []

    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()
            # Remove old calls
            self.calls = [c for c in self.calls if now - c < self.time_window]

            if len(self.calls) >= self.max_calls:
                raise Exception("Rate limit exceeded")

            self.calls.append(now)
            return await func(*args, **kwargs)
        return wrapper

# Usage:
@RateLimiter(max_calls=10, time_window=60)
async def process_query(query):
    # Your code here
    pass
```

### 4. Input Validation

```python
# Validate user inputs
def validate_query(query: str) -> bool:
    """Validate user query for security."""

    # Check length
    if len(query) > 1000:
        return False

    # Check for SQL injection patterns
    sql_patterns = ["DROP TABLE", "DELETE FROM", "INSERT INTO"]
    if any(pattern in query.upper() for pattern in sql_patterns):
        return False

    # Check for XSS patterns
    xss_patterns = ["<script>", "javascript:", "onerror="]
    if any(pattern in query.lower() for pattern in xss_patterns):
        return False

    return True
```

---

## Monitoring and Logging

### 1. Application Logging

Create `src/utils/logger.py`:

```python
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name: str) -> logging.Logger:
    """Setup logger with file and console handlers."""

    logger = logging.getLogger(name)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        f"logs/{name}.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)s - %(message)s'
    ))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
```

### 2. Performance Monitoring

```python
# Add to app_full_agent.py
import time
from datetime import datetime

# Track metrics
if "performance_metrics" not in st.session_state:
    st.session_state.performance_metrics = []

# After each query
st.session_state.performance_metrics.append({
    "timestamp": datetime.now(),
    "query": prompt,
    "mode": result.get("mode"),
    "execution_time": result.get("execution_time"),
    "total_time": result.get("total_time"),
})

# Show metrics in sidebar
with st.sidebar:
    st.subheader("Performance Metrics")
    if st.session_state.performance_metrics:
        recent_metrics = st.session_state.performance_metrics[-10:]
        avg_time = sum(m["total_time"] for m in recent_metrics) / len(recent_metrics)
        st.metric("Avg Response Time", f"{avg_time:.2f}s")
```

### 3. Error Tracking

```python
# Add error tracking wrapper
import traceback

def track_error(error: Exception, context: dict):
    """Track errors for analysis."""

    error_info = {
        "timestamp": datetime.now(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "context": context
    }

    # Log to file
    logger.error(f"Error occurred: {error_info}")

    # Optional: Send to error tracking service (Sentry, etc.)
    # sentry_sdk.capture_exception(error)
```

---

## Scaling Considerations

### 1. Horizontal Scaling

For high traffic, run multiple instances behind a load balancer:

```yaml
# docker-compose-scale.yml
version: '3.8'

services:
  ai-stock-advisor:
    build: .
    env_file: .env
    deploy:
      replicas: 3  # Run 3 instances

  nginx-lb:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
    depends_on:
      - ai-stock-advisor
```

### 2. Caching Strategy

Implement Redis for shared caching:

```python
import redis
import json

class RedisCache:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0
        )

    def get(self, key: str):
        value = self.redis_client.get(key)
        return json.loads(value) if value else None

    def set(self, key: str, value, ttl: int = 300):
        self.redis_client.setex(
            key, ttl, json.dumps(value)
        )
```

### 3. Database for Conversations

Use PostgreSQL or MongoDB for conversation history:

```python
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    session_id = Column(String, index=True)
    timestamp = Column(DateTime)
    query = Column(Text)
    response = Column(Text)
    metadata = Column(Text)  # JSON
```

---

## Troubleshooting

### Common Issues

#### 1. OpenAI API Errors

**Error: "Rate limit exceeded"**
```python
# Solution: Implement exponential backoff
import time

async def call_with_retry(func, max_retries=3):
    for i in range(max_retries):
        try:
            return await func()
        except openai.RateLimitError:
            if i < max_retries - 1:
                wait_time = 2 ** i
                time.sleep(wait_time)
            else:
                raise
```

**Error: "Invalid API key"**
- Check .env file exists and is loaded
- Verify API key format (starts with "sk-")
- Check key permissions in OpenAI dashboard

#### 2. MCP Connection Errors

**Error: "Cannot connect to MCP server"**
- Verify MCP_SERVER_URL in .env
- Check network connectivity
- Verify MCP server is running
- Check firewall rules

#### 3. Memory Issues

**Error: "Out of memory"**
- Reduce max_tokens in agents
- Implement conversation history pruning
- Increase server RAM
- Use smaller model (gpt-4o-mini)

#### 4. Slow Performance

**Solutions:**
- Enable routing cache
- Add MCP result caching
- Use connection pooling (already implemented)
- Scale horizontally
- Optimize database queries

---

## Production Checklist

Before deploying to production:

- [ ] All tests passing
- [ ] Environment variables configured
- [ ] API keys secured
- [ ] SSL certificate installed
- [ ] Monitoring enabled
- [ ] Logging configured
- [ ] Error tracking setup
- [ ] Backup strategy in place
- [ ] Rate limiting enabled
- [ ] Authentication implemented
- [ ] Load testing completed
- [ ] Documentation updated
- [ ] Rollback plan ready

---

## Support and Maintenance

### Regular Maintenance Tasks

**Daily:**
- Monitor error logs
- Check API usage/costs
- Verify system health

**Weekly:**
- Review performance metrics
- Analyze user patterns
- Check for OpenAI API updates

**Monthly:**
- Rotate API keys
- Update dependencies
- Review and optimize costs
- Backup configuration

### Getting Help

- OpenAI API Docs: https://platform.openai.com/docs
- Streamlit Docs: https://docs.streamlit.io
- GitHub Issues: (your-repo-url)/issues

---

## Cost Estimation

### OpenAI API Costs (as of 2025)

**gpt-4o-mini:**
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens
- Typical query cost: $0.001 - $0.003

**gpt-4o:**
- Input: $2.50 per 1M tokens
- Output: $10.00 per 1M tokens
- Typical query cost: $0.02 - $0.05

### Monthly Cost Estimates

**Low Traffic (100 queries/day):**
- gpt-4o-mini only: ~$10/month
- gpt-4o for orchestrator: ~$50/month

**Medium Traffic (1000 queries/day):**
- gpt-4o-mini only: ~$100/month
- gpt-4o for orchestrator: ~$500/month

**High Traffic (10000 queries/day):**
- gpt-4o-mini only: ~$1000/month
- gpt-4o for orchestrator: ~$5000/month

### Cost Optimization Tips

1. Maximize DIRECT mode usage (0% AI cost)
2. Use routing cache (reduces routing calls)
3. Implement response caching
4. Use gpt-4o-mini where possible
5. Set billing limits in OpenAI dashboard

---

## Next Steps

After successful deployment:

1. **Monitor Performance**: Track metrics for 1-2 weeks
2. **Optimize**: Identify and fix bottlenecks
3. **Scale**: Add resources as needed
4. **Iterate**: Improve based on user feedback
5. **Document**: Update docs with learnings

---

## Additional Resources

- [OpenAI Best Practices](https://platform.openai.com/docs/guides/production-best-practices)
- [Streamlit Deployment Guide](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app)
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)

---

**Version:** 1.0
**Last Updated:** 2026-01-08
**Author:** AI Stock Advisor Team
