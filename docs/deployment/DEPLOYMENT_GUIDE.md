# ReflectAI Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start Deployment](#quick-start-deployment)
3. [Environment Setup](#environment-setup)
4. [Local Development](#local-development)
5. [Docker Deployment](#docker-deployment)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [Cloud Deployment](#cloud-deployment)
8. [Configuration](#configuration)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- Python 3.11+
- Docker 24.0+
- Docker Compose 2.20+
- kubectl 1.28+ (for Kubernetes deployment)
- Helm 3.12+ (optional, for Helm deployment)
- AWS CLI 2.13+ (for AWS deployment)

### System Requirements

#### Minimum (Development)
- CPU: 2 cores
- RAM: 4 GB
- Storage: 10 GB

#### Recommended (Production)
- CPU: 4+ cores
- RAM: 16+ GB
- Storage: 100+ GB SSD

## Quick Start Deployment

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd reflectai-platform

# Create environment configuration
cp .env.example .env
# Edit .env with your specific values

# Verify cluster access (for Kubernetes deployment)
kubectl cluster-info
kubectl get nodes
```

### 2. Infrastructure Deployment

```bash
# Deploy infrastructure components
./scripts/deploy-infrastructure.sh

# Verify infrastructure
kubectl get pods -n reflectai
kubectl get pvc -n reflectai
```

### 3. Application Deployment

```bash
# Build and deploy application
./scripts/deploy-application.sh production

# Verify deployment
kubectl get deployments -n reflectai
kubectl get services -n reflectai
```

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/reflectai/platform.git
cd reflectai-platform
```

### 2. Install Dependencies

```bash
# Using PDM (recommended)
pdm install

# Or using pip
pip install -r requirements.txt
```

### 3. Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Database
DATABASE_URL=postgresql://reflectai:password@localhost:5432/reflectai

# Redis
REDIS_URL=redis://localhost:6379/0

# Slack
SLACK_BOT_TOKEN=replace_with_slack_bot_token
SLACK_APP_TOKEN=xapp-your-app-token

# OpenAI
OPENAI_API_KEY=sk-your-api-key

# AWS (optional)
AWS_REGION=us-west-2
S3_BUCKET=reflectai-reports
```

## Local Development

### Using Make

```bash
# Setup everything
make setup

# Run development server
make dev

# Run tests
make test

# Format and lint
make format
make lint
```

### Manual Setup

1. **Start Database and Redis**:

```bash
# PostgreSQL
docker run -d \
  --name reflectai-postgres \
  -e POSTGRES_DB=reflectai \
  -e POSTGRES_USER=reflectai \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:15-alpine

# Redis
docker run -d \
  --name reflectai-redis \
  -p 6379:6379 \
  redis:7-alpine
```

2. **Run Migrations**:

```bash
python scripts/manage_migrations.py upgrade
```

3. **Start Application**:

```bash
python src/main.py
```

## Docker Deployment

### Development Environment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

### Production Environment

```bash
# Build production image
docker build -t reflectai/app:v2.0.0 .

# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Scale application
docker-compose -f docker-compose.prod.yml up -d --scale app=3
```

## Kubernetes Deployment

### Prerequisites
- **Kubernetes Cluster**: v1.25+ with at least 6 nodes (4 CPU, 16GB RAM each)
- **Helm**: v3.13+
- **kubectl**: v1.25+
- **Storage**: 500GB+ available storage with fast SSD storage class

### Step 1: Namespace and RBAC Setup

```bash
kubectl create namespace reflectai
kubectl label namespace reflectai istio-injection=enabled monitoring=enabled

# Apply RBAC configuration
kubectl apply -f k8s/00-namespace.yaml
```

### Step 2: Secrets Management

```bash
# Database credentials
kubectl create secret generic postgres-credentials \
  --from-literal=username=reflectai_user \
  --from-literal=password='<secure-password>' \
  --from-literal=database=reflectai \
  -n reflectai

# Redis credentials
kubectl create secret generic redis-credentials \
  --from-literal=password='<secure-redis-password>' \
  -n reflectai

# LLM credentials
kubectl create secret generic llm-credentials \
  --from-literal=api-key='<llm-api-key>' \
  --from-literal=oauth-client-id='<oauth-client-id>' \
  --from-literal=oauth-client-secret='<oauth-client-secret>' \
  -n reflectai

# Slack credentials
kubectl create secret generic slack-credentials \
  --from-literal=bot-token='<slack-bot-token>' \
  --from-literal=app-token='<slack-app-token>' \
  --from-literal=signing-secret='<slack-signing-secret>' \
  -n reflectai
```

### Step 3: Infrastructure Components

#### PostgreSQL with CloudNativePG
```bash
# Install CloudNativePG operator
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm install cnpg cnpg/cloudnative-pg --namespace cnpg-system --create-namespace

# Deploy PostgreSQL cluster
kubectl apply -f k8s/postgresql-cluster.yaml
```

#### Redis Cluster
```bash
# Install Redis operator
kubectl apply -f https://raw.githubusercontent.com/spotahome/redis-operator/master/manifests/databases.spotahome.com_redisfailovers.yaml

# Deploy Redis cluster
kubectl apply -f k8s/redis-cluster.yaml
```

### Step 4: Deploy Application

#### Using Helm
```bash
# Package and deploy
helm package helm/reflectai
helm install reflectai-core ./reflectai-*.tgz \
  --namespace reflectai \
  --values helm/reflectai/values-production.yaml \
  --set image.tag=${VERSION} \
  --wait \
  --timeout=600s
```

#### Using kubectl
```bash
# Apply all configurations
kubectl apply -f k8s/ -n reflectai

# Wait for deployment
kubectl rollout status deployment/reflectai-app -n reflectai

# Check pods
kubectl get pods -n reflectai
```

### Step 5: Configure Ingress

```bash
# Apply ingress configuration with TLS
kubectl apply -f k8s/ingress.yaml

# Verify ingress
kubectl get ingress -n reflectai
kubectl describe ingress reflectai-ingress -n reflectai
```

### Step 6: Verification

```bash
# Check all pods are running
kubectl get pods -n reflectai

# Check services
kubectl get services -n reflectai

# Test health endpoints
kubectl run test-pod --image=curlimages/curl:latest --rm -i --restart=Never -- \
  curl -f http://slack-gateway:8000/health

# View logs
kubectl logs -l app=reflectai -n reflectai --tail=100
```

## Cloud Deployment

### AWS EKS Deployment

1. **Create EKS Cluster**:

```bash
eksctl create cluster \
  --name reflectai-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5
```

2. **Install AWS Load Balancer Controller**:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=reflectai-cluster
```

3. **Deploy Application**:

```bash
# Use deployment script
./scripts/deploy.sh production
```

### AWS ECS Deployment

1. **Create Task Definition**:

```json
{
  "family": "reflectai-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "reflectai",
      "image": "reflectai/app:v2.0.0",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"}
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:..."
        }
      ]
    }
  ]
}
```

2. **Create Service**:

```bash
aws ecs create-service \
  --cluster reflectai-cluster \
  --service-name reflectai-service \
  --task-definition reflectai-app:1 \
  --desired-count 3 \
  --launch-type FARGATE
```

### Google Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/reflectai

# Deploy to Cloud Run
gcloud run deploy reflectai \
  --image gcr.io/PROJECT_ID/reflectai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production"
```

## Configuration

### Application Configuration

Configuration is managed through:

1. **Environment Variables** (highest priority)
2. **Configuration Files** (`config/environments/*.yaml`)
3. **Default Values** (lowest priority)

### Key Configuration Files

#### `config/environments/production.yaml`

```yaml
app:
  name: reflectai
  version: 2.0.0
  debug: false
  log_level: INFO

database:
  pool_size: 20
  max_overflow: 40
  echo_sql: false

redis:
  max_connections: 50
  decode_responses: true

slack:
  rate_limit: 30
  timeout: 10

features:
  advanced_analytics: true
  pdf_reports: true
  batch_processing: true
```

### Security Configuration

#### TLS/SSL

```nginx
# nginx/nginx.conf
server {
    listen 443 ssl http2;
    server_name api.reflectai.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://reflectai-app:8000;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Network Policies

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: reflectai-network-policy
  namespace: reflectai
spec:
  podSelector:
    matchLabels:
      app: reflectai
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: reflectai
    ports:
    - protocol: TCP
      port: 8000
```

## Monitoring

### Prometheus Metrics

Metrics are exposed at `/metrics` endpoint:

```yaml
# monitoring/prometheus.yml
scrape_configs:
  - job_name: 'reflectai'
    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - reflectai
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      action: keep
      regex: true
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
      action: replace
      target_label: __metrics_path__
      regex: (.+)
```

### Grafana Dashboards

Import provided dashboards:

1. **Application Dashboard** (`monitoring/grafana/dashboards/application.json`)
2. **Database Dashboard** (`monitoring/grafana/dashboards/database.json`)
3. **Redis Dashboard** (`monitoring/grafana/dashboards/redis.json`)

### Health Checks

```bash
# Liveness probe
curl http://localhost:9090/health/live

# Readiness probe
curl http://localhost:9090/health/ready

# Detailed health
curl http://localhost:9090/health/details
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check PostgreSQL status
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Test connection
psql -h localhost -U reflectai -d reflectai
```

#### 2. Redis Connection Failed

```bash
# Check Redis status
docker-compose ps redis

# Test connection
redis-cli ping
```

#### 3. Slack Bot Not Responding

```bash
# Verify tokens
python -c "from src.integrations.slack.client import SlackClient; client = SlackClient(); print(client.test_connection())"

# Check event subscriptions
curl -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  https://slack.com/api/apps.event.authorizations.list
```

#### 4. Pod CrashLoopBackOff

```bash
# Get pod logs
kubectl logs -n reflectai <pod-name> --previous

# Describe pod
kubectl describe pod -n reflectai <pod-name>

# Check events
kubectl get events -n reflectai --sort-by='.lastTimestamp'
```

### Performance Tuning

#### Database

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM activities WHERE user_id = '...';

-- Check slow queries
SELECT query, calls, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Vacuum and analyze
VACUUM ANALYZE;
```

#### Redis

```bash
# Monitor Redis performance
redis-cli --latency

# Check memory usage
redis-cli INFO memory

# Enable slow log
redis-cli CONFIG SET slowlog-log-slower-than 10000
redis-cli SLOWLOG GET 10
```

### Backup and Recovery

#### Database Backup

```bash
# Backup
pg_dump -h localhost -U reflectai -d reflectai > backup_$(date +%Y%m%d).sql

# Restore
psql -h localhost -U reflectai -d reflectai < backup_20240115.sql
```

#### Automated Backups

```yaml
# k8s/cronjob-backup.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: reflectai
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15-alpine
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h postgres-service -U reflectai -d reflectai | \
              aws s3 cp - s3://reflectai-backups/$(date +%Y%m%d).sql
```

## Support

- **Documentation**: https://docs.reflectai.com
- **GitHub Issues**: https://github.com/reflectai/platform/issues
- **Slack Community**: https://reflectai.slack.com
- **Email Support**: support@reflectai.com