# Orbia Backend Deployment Guide

This guide covers deploying the Orbia backend application using Docker and Docker Compose.

## 🚀 Quick Start

1. **Clone and setup environment**:
   ```bash
   git clone <your-repo>
   cd orbia-backend
   cp example.env .env
   # Edit .env with your actual values
   ```

2. **Deploy with one command**:
   ```bash
   ./deploy.sh
   ```

## 📋 Prerequisites

- Docker and Docker Compose installed
- Required API keys (OpenAI, etc.)
- Domain name (for production)

## 🔧 Environment Configuration

### Required Environment Variables

Before deployment, ensure these variables are set in your `.env` file:

```bash
# Essential for security
JWT_SECRET_KEY=your_strong_secret_key_here

# Required for AI functionality
OPENAI_API_KEY=sk-your_openai_api_key

# Optional but recommended
GEMINI_API_KEY=your_gemini_api_key
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
```

### Generate JWT Secret

```bash
# Generate a secure JWT secret
openssl rand -hex 32
```

## 🐳 Docker Deployment

### Option 1: Using the deployment script (Recommended)

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### Option 2: Manual deployment

```bash
# Build the image
docker build -t orbia:latest .

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

## 🔍 Health Checks

The application includes built-in health checks:

- **Application Health**: `http://localhost:8000/_Health`
- **Metrics**: `http://localhost:8000/metrics`
- **Docker Health**: `docker-compose ps` shows health status

## 📊 Monitoring

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f fastapi-app
docker-compose logs -f redis
```

### Metrics

Prometheus metrics are available at `/metrics` endpoint.

## 🔧 Production Optimizations

### Security Features

- ✅ Non-root user in Docker container
- ✅ Disabled API docs in production (unless explicitly enabled)
- ✅ Restricted CORS origins in production
- ✅ Environment-based configuration

### Performance Features

- ✅ Multi-worker Gunicorn setup
- ✅ Redis for caching and memory storage
- ✅ Health checks for container orchestration
- ✅ Optimized Docker image with multi-stage build

## 🌐 Production Deployment

### Environment Variables for Production

```bash
NODE_ENV=production
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ENABLE_DOCS=false  # Keep API docs disabled
LOG_LEVEL=INFO
CONCISE_LOGGING=true
```

### Reverse Proxy Setup (Nginx)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL/HTTPS Setup

Use Certbot for free SSL certificates:

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com
```

## 🔄 Updates and Maintenance

### Updating the Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
./deploy.sh
```

### Backup and Restore

```bash
# Backup Redis data
docker-compose exec redis redis-cli BGSAVE

# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/
```

## 🐛 Troubleshooting

### Common Issues

1. **Container won't start**:
   ```bash
   # Check logs
   docker-compose logs fastapi-app
   
   # Check environment variables
   docker-compose exec fastapi-app env | grep -E "(OPENAI|JWT)"
   ```

2. **Health check failing**:
   ```bash
   # Test health endpoint manually
   curl http://localhost:8000/_Health
   
   # Check if port is accessible
   netstat -tlnp | grep 8000
   ```

3. **Redis connection issues**:
   ```bash
   # Test Redis connectivity
   docker-compose exec redis redis-cli ping
   
   # Check Redis logs
   docker-compose logs redis
   ```

4. **Permission issues**:
   ```bash
   # Fix log directory permissions
   sudo chown -R 1000:1000 logs/
   ```

### Performance Issues

1. **High memory usage**:
   - Reduce Gunicorn workers in docker-compose.yml
   - Monitor with `docker stats`

2. **Slow responses**:
   - Check API key rate limits
   - Monitor with `/metrics` endpoint

### Environment Issues

1. **Missing environment variables**:
   ```bash
   # Validate .env file
   grep -E "^[A-Z_]+=.+" .env | wc -l
   
   # Check for placeholder values
   grep -E "(your_|CHANGE_THIS)" .env
   ```

## 📞 Support

For deployment issues:

1. Check the logs: `docker-compose logs -f`
2. Verify environment variables are set correctly
3. Ensure all required API keys are valid
4. Check network connectivity and firewall settings

## 🔗 Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart fastapi-app

# View logs
docker-compose logs -f

# Execute commands in container
docker-compose exec fastapi-app bash

# Check resource usage
docker stats

# Clean up unused resources
docker system prune -f
``` 