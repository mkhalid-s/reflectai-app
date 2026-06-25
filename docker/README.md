# Docker Configuration for ReflectAI Platform

This directory contains streamlined Docker configurations fully integrated with the `./dev` CLI tool.

## 📁 Structure

```
docker/
├── README.md                           # This file
├── docker-compose.dev.yml             # Development overrides
├── docker-compose.prod.yml            # Production overrides
├── docker-compose.test.yml            # Testing configuration
├── docker-compose.monitoring.yml      # Monitoring stack
├── nginx/
│   └── nginx.conf                     # Nginx reverse proxy config
└── monitoring/
    ├── prometheus.yml                 # Metrics collection config
    ├── loki-config.yml                # Log aggregation config
    ├── promtail-config.yml            # Log shipping config
    └── grafana/
        ├── datasources/               # Data source configurations
        └── dashboards/                # Dashboard configurations
```

## 🚀 Quick Start

All Docker operations are managed through the `./dev` CLI:

```bash
# Start development environment
./rai docker up dev

# View logs
./rai docker logs app

# Stop containers
./rai docker down
```

## 🐳 Docker Commands

### Building Images

```bash
# Build development image (default)
./rai docker build

# Build production image
./rai docker build production

# Build with no cache
./rai docker build development --no-cache
```

### Managing Containers

```bash
# Start containers
./rai docker up           # Default environment
./rai docker up dev       # Development with tools
./rai docker up prod      # Production environment
./rai docker up test      # Run tests
./rai docker up monitoring # Start monitoring stack

# Stop containers
./rai docker down

# Stop and remove volumes (CAUTION: deletes data)
./rai docker down --volumes

# Restart containers
./rai docker restart      # All containers
./rai docker restart app  # Specific service
```

### Monitoring & Debugging

```bash
# View logs
./rai docker logs app          # Last 50 lines
./rai docker logs app --follow # Follow logs
./rai docker logs redis       # Specific service

# Check status
./rai docker status

# Execute commands in container
./rai docker exec app         # Get bash shell
./rai docker exec app ls -la  # Run specific command
./rai docker exec postgres psql -U reflectai
```

### Cleanup

```bash
# Clean Docker resources
./rai docker clean      # Remove stopped containers, unused networks, dangling images

# Deep clean (includes all unused images)
./rai docker clean --all
```

## 🌍 Environments

### Development (`dev`)

Full development stack with debugging tools:
- Application with hot reload
- PostgreSQL database
- Redis cache
- Redis Commander (http://localhost:8081)
- PgAdmin (http://localhost:5050)

```bash
./rai docker up dev
```

### Production (`prod`)

Production-ready configuration:
- Optimized builds
- Nginx reverse proxy
- Monitoring stack (Prometheus, Grafana)
- Security hardening
- Resource limits

```bash
./rai docker up prod
```

### Testing (`test`)

Isolated test environment:
- Test database (in-memory)
- Test Redis (no persistence)
- Coverage reports

```bash
./rai docker test
```

### Monitoring (`monitoring`)

Full observability stack:
- Prometheus (metrics)
- Grafana (dashboards)
- Loki (logs)
- Exporters for all services

```bash
./rai docker up monitoring
```

## 📊 Service Ports

| Service | Port | Environment | Description |
|---------|------|-------------|-------------|
| App | 3000 | All | Main application |
| Health | 8090 | All | Health check endpoint |
| Metrics | 8080 | All | Prometheus metrics |
| PostgreSQL | 5432 | Dev/Test | Database |
| Redis | 6379 | Dev/Test | Cache |
| Redis Commander | 8081 | Dev | Redis UI |
| PgAdmin | 5050 | Dev | Database UI |
| Prometheus | 9090 | Monitoring | Metrics server |
| Grafana | 3001 | Monitoring | Dashboards |
| Loki | 3100 | Monitoring | Log aggregation |

## 🔧 Configuration

### Environment Variables

Create `.env` file from template:
```bash
cp .env.example .env
```

Key variables:
```env
# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=false

# Database
DB_PASSWORD=devpassword
DB_PORT=5432

# Redis
REDIS_PASSWORD=devpassword
REDIS_PORT=6379

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# LLM
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Docker Build Args

Customize builds with arguments:
```bash
# Specify Python version
docker build --build-arg PYTHON_VERSION=3.11 .

# Specify PDM version
docker build --build-arg PDM_VERSION=2.20.1 .
```

### Resource Limits

Production resource limits:
- CPU: 2 cores (limit), 1 core (reservation)
- Memory: 2GB (limit), 1GB (reservation)

Adjust in `docker-compose.prod.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

## 🏗️ Multi-Stage Builds

The Dockerfile uses multi-stage builds for optimization:

1. **base**: Base Python image with environment setup
2. **builder**: Dependency installation
3. **development**: Full dev environment with tools
4. **testing**: Test runner with coverage
5. **production**: Minimal production image
6. **production-alpine**: Ultra-light Alpine-based image

## 🔒 Security

Production builds include:
- Non-root user execution
- Read-only filesystem where possible
- Security headers in Nginx
- Network isolation
- Secret management via environment variables

## 🚨 Troubleshooting

### Container won't start
```bash
# Check logs
./rai docker logs app

# Check configuration
./rai docker exec app env | grep -E "DATABASE|REDIS"
```

### Database connection issues
```bash
# Test database connection
./rai docker exec postgres pg_isready

# Connect to database
./rai docker exec postgres psql -U reflectai
```

### Redis connection issues
```bash
# Test Redis connection
./rai docker exec redis redis-cli ping

# Check Redis logs
./rai docker logs redis
```

### Port conflicts
```bash
# Check what's using a port
lsof -i :3000

# Use different ports in .env
APP_PORT=3001
```

### Clean start
```bash
# Complete cleanup and fresh start
./rai docker down --volumes
./rai docker clean --all
./rai docker up dev --build
```

## 🎯 Best Practices

### Development
1. Use `./rai docker up dev` for local development
2. Keep containers running for faster iteration
3. Use volume mounts for code changes
4. Check logs frequently

### Testing
1. Always test in Docker before deployment
2. Use `./rai docker test` for CI/CD
3. Verify all services are healthy

### Production
1. Build production images with `./rai docker build production`
2. Use specific tags for versioning
3. Always test in staging first
4. Monitor resource usage

### Cleanup
1. Regular cleanup with `./rai docker clean`
2. Remove unused volumes periodically
3. Prune old images to save space

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Best Practices for Dockerfiles](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Multi-stage Builds](https://docs.docker.com/develop/develop-images/multistage-build/)

## 💡 Tips

1. **Fast rebuilds**: Use BuildKit for faster builds
   ```bash
   DOCKER_BUILDKIT=1 ./rai docker build
   ```

2. **Debug containers**: Keep failed containers for debugging
   ```bash
   docker compose up --abort-on-container-exit --exit-code-from app
   ```

3. **Monitor resources**: Watch container resources
   ```bash
   docker stats
   ```

4. **Export/Import data**: Backup and restore volumes
   ```bash
   # Backup
   docker run --rm -v reflectai_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data

   # Restore
   docker run --rm -v reflectai_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres-backup.tar.gz -C /
   ```

## 🆘 Support

For Docker-related issues:
1. Check this README
2. Run `./rai docker status` for diagnostics
3. Check logs with `./rai docker logs [service]`
4. Clean and rebuild if needed

---

**Remember**: All Docker operations are managed through `./rai docker` commands for consistency!