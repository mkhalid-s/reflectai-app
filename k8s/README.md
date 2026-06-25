# Kubernetes Deployment Configuration

This directory contains production-ready Kubernetes manifests for deploying the ReflectAI platform.

## 📁 Directory Structure

```
k8s/
├── README.md                   # This file
├── kind-cluster.yaml          # Local kind cluster config (auto-generated)
├── configmap.yaml             # Application configuration
├── deployment.yaml            # Main application deployment
├── hpa.yaml                   # Horizontal Pod Autoscaler
├── ingress.yaml               # Ingress/Load balancer
├── namespace.yaml             # Namespace definition
├── pdb.yaml                   # Pod Disruption Budget
├── rbac.yaml                  # Role-based access control
├── secrets.yaml               # Secret management
├── service.yaml               # Service definition
├── monitoring/                # Observability stack
│   ├── alertmanager.yaml     # Alert management
│   ├── grafana.yaml          # Metrics dashboards
│   ├── loki.yaml             # Log aggregation
│   ├── prometheus.yaml       # Metrics collection
│   └── rbac.yaml             # Monitoring RBAC
└── overlays/                  # Environment-specific configs
    ├── production/           # Production overrides
    └── staging/              # Staging overrides
```

## 🚀 Quick Start

### Prerequisites
- `kubectl` installed and configured
- Docker installed
- `kind` or `minikube` for local development

### Local Development

```bash
# Setup local Kubernetes cluster
./rai k8s setup

# Deploy the application
./rai k8s deploy local

# Check deployment status
./rai k8s status

# Access the application
./rai k8s port-forward

# View logs
./rai k8s logs

# Clean up
./rai k8s destroy local
```

### Staging Deployment

```bash
# Deploy to staging
./rai k8s deploy staging

# Check status
./rai k8s status

# View logs
./rai k8s logs --follow
```

### Production Deployment

```bash
# Use production deployment script
./rai k8s deploy production
```

## 🏗️ Architecture Overview

### Application Components

| Component | Description | Replicas | Resources |
|-----------|-------------|----------|-----------|
| **reflectai-app** | Main FastAPI application | 3 | 500m CPU, 1Gi RAM |
| **postgres** | PostgreSQL database | 1 | 250m CPU, 512Mi RAM |
| **redis** | Redis cache | 1 | 100m CPU, 256Mi RAM |

### Monitoring Stack

| Component | Description | Purpose |
|-----------|-------------|---------|
| **Prometheus** | Metrics collection | Application & infrastructure metrics |
| **Grafana** | Visualization | Dashboards and alerting |
| **Loki** | Log aggregation | Centralized logging |
| **AlertManager** | Alert routing | Notification management |

### Networking

- **Service**: ClusterIP service for internal communication
- **Ingress**: NGINX ingress for external access
- **NetworkPolicies**: Security between services

### Security

- **RBAC**: Role-based access control
- **SecurityContext**: Non-root containers
- **PodSecurityPolicy**: Security standards
- **Secrets**: Encrypted configuration

## 📋 Configuration Details

### Environment Variables

The application uses these environment variables:

```yaml
# Core Configuration
APP_ENV: production|staging|local
LOG_LEVEL: INFO|DEBUG|WARNING
DEBUG: false|true

# Database
DATABASE_URL: postgresql://...
REDIS_URL: redis://...

# External Services
SLACK_BOT_TOKEN: xoxb-...
OPENAI_API_KEY: sk-...

# Monitoring
PROMETHEUS_METRICS_PORT: 8080
HEALTH_CHECK_PORT: 9090
```

### Resource Requirements

#### Minimum Resources
- **CPU**: 1.5 cores total
- **Memory**: 2GB total
- **Storage**: 10GB persistent

#### Recommended Resources
- **CPU**: 4 cores total
- **Memory**: 8GB total
- **Storage**: 50GB persistent

### Scaling Configuration

- **HPA Target**: 70% CPU utilization
- **Min Replicas**: 3
- **Max Replicas**: 10
- **Scale up**: 2 pods every 60s
- **Scale down**: 1 pod every 300s

## 🔧 Customization

### Environment-Specific Changes

Use Kustomize overlays for environment-specific configurations:

```yaml
# overlays/staging/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- ../../base

# Override image tag
images:
- name: reflectai/platform
  newTag: staging-v1.2.0

# Override replicas
replicas:
- name: reflectai-app
  count: 2

# Environment-specific config
configMapGenerator:
- name: reflectai-config
  literals:
  - APP_ENV=staging
  - LOG_LEVEL=DEBUG
```

### Adding New Services

1. Create service YAML in base directory
2. Add to overlays if environment-specific
3. Update RBAC if needed
4. Add monitoring configuration
5. Update ingress rules

### Secrets Management

Secrets are managed through Kubernetes secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: reflectai-secrets
type: Opaque
data:
  DATABASE_PASSWORD: <base64-encoded>
  SLACK_BOT_TOKEN: <base64-encoded>
  OPENAI_API_KEY: <base64-encoded>
```

## 🔍 Monitoring & Observability

### Metrics

Application exposes metrics on port 8080:
- Request duration
- Request count by endpoint
- Error rates
- Database connection pool
- Redis operations

### Logging

All logs are structured JSON:
- Application logs to stdout
- Access logs to stdout
- Error logs include trace IDs
- Logs aggregated by Loki

### Health Checks

- **Liveness probe**: `/health` on port 9090
- **Readiness probe**: `/ready` on port 9090
- **Startup probe**: `/health` with extended timeout

### Dashboards

Grafana includes these dashboards:
- Application overview
- Request metrics
- Database performance
- Infrastructure metrics
- Error tracking

## 🚨 Troubleshooting

### Common Issues

#### Pods Not Starting
```bash
# Check pod status
./rai k8s status

# Check events
kubectl describe pod <pod-name> -n reflectai

# Check logs
./rai k8s logs
```

#### Service Not Accessible
```bash
# Check service endpoints
kubectl get endpoints -n reflectai

# Test service connectivity
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup reflectai-service
```

#### High Resource Usage
```bash
# Check resource usage
kubectl top pods -n reflectai

# Check HPA status
kubectl get hpa -n reflectai

# Scale manually if needed
kubectl scale deployment reflectai-app --replicas=5 -n reflectai
```

#### Database Issues
```bash
# Check database pod
kubectl logs <postgres-pod> -n reflectai

# Connect to database
kubectl exec -it <postgres-pod> -n reflectai -- psql -U reflectai
```

### Performance Tuning

1. **CPU Limits**: Adjust based on load testing
2. **Memory Limits**: Monitor for OOM kills
3. **Replica Count**: Use HPA recommendations
4. **Database**: Tune connection pools
5. **Redis**: Monitor cache hit rates

### Security Checklist

- [ ] Non-root containers
- [ ] Read-only root filesystem
- [ ] Resource limits set
- [ ] RBAC properly configured
- [ ] Secrets not in plain text
- [ ] Network policies in place
- [ ] Image vulnerability scanning

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [NGINX Ingress](https://kubernetes.github.io/ingress-nginx/)

## 🆘 Support

For deployment issues:
1. Check this README
2. Run `./rai k8s status` for diagnostics
3. Check application logs with `./rai k8s logs`
4. Review monitoring dashboards
5. Create an issue with logs and configuration

---

**Remember**: Always test in staging before production deployment!