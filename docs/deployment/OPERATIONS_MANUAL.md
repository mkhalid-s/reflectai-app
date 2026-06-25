# ReflectAI Operations Manual

## Daily Operations

### Health Monitoring

#### System Health Checks
```bash
# Check overall system health
kubectl get pods -n reflectai
kubectl get services -n reflectai
kubectl get pvc -n reflectai

# Check resource usage
kubectl top pods -n reflectai
kubectl top nodes

# Verify ingress status
kubectl get ingress -n reflectai
```

#### Application Health Endpoints
```bash
# Health check all services
curl https://api.reflectai.company.com/health
curl https://api.reflectai.company.com/slack-gateway/health
curl https://api.reflectai.company.com/agent-orchestrator/health
curl https://api.reflectai.company.com/health-service/health/detailed
```

### Log Monitoring

#### Centralized Logging
```bash
# View application logs
kubectl logs -l app=reflectai-core -n reflectai --tail=100 -f

# View specific service logs
kubectl logs -l app=slack-gateway -n reflectai --tail=50

# Search for errors
kubectl logs -l app=reflectai-core -n reflectai | grep -i error

# View structured logs with jq
kubectl logs -l app=reflectai-core -n reflectai | jq '.'
```

#### Log Analysis Queries
```bash
# Find high error rates
kubectl logs -l app=reflectai-core -n reflectai | \
  jq 'select(.level == "ERROR")' | \
  jq -r '.timestamp + " " + .message'

# Track multi-agent executions
kubectl logs -l app=agent-orchestrator -n reflectai | \
  jq 'select(.baggage.crew_id != null)'

# Monitor LLM token usage
kubectl logs -l app=reflectai-core -n reflectai | \
  jq 'select(.extra.tokens_used != null)'
```

## Backup and Recovery

### Database Backup

#### Automated Backup Script
```bash
#!/bin/bash
# scripts/backup-database.sh

set -e

NAMESPACE="reflectai"
BACKUP_DIR="/backups/postgresql"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

echo "Starting PostgreSQL backup..."

# Get primary pod
PRIMARY_POD=$(kubectl get pods -n $NAMESPACE -l postgresql=primary -o jsonpath='{.items[0].metadata.name}')

# Perform backup
kubectl exec -n $NAMESPACE $PRIMARY_POD -- \
  pg_dump -U reflectai_user -d reflectai \
  --verbose --clean --if-exists \
  --format=custom \
  > $BACKUP_DIR/reflectai_backup_$TIMESTAMP.dump

# Compress backup
gzip $BACKUP_DIR/reflectai_backup_$TIMESTAMP.dump

# Upload to object storage (if configured)
if [ -n "$S3_BUCKET" ]; then
  aws s3 cp $BACKUP_DIR/reflectai_backup_$TIMESTAMP.dump.gz \
    s3://$S3_BUCKET/database/
fi

# Clean up old backups
find $BACKUP_DIR -name "*.dump.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: reflectai_backup_$TIMESTAMP.dump.gz"
```

#### Database Recovery
```bash
#!/bin/bash
# scripts/restore-database.sh

BACKUP_FILE=$1
NAMESPACE="reflectai"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file>"
  exit 1
fi

echo "Restoring database from $BACKUP_FILE..."

# Get primary pod
PRIMARY_POD=$(kubectl get pods -n $NAMESPACE -l postgresql=primary -o jsonpath='{.items[0].metadata.name}')

# Copy backup to pod
kubectl cp $BACKUP_FILE $NAMESPACE/$PRIMARY_POD:/tmp/restore.dump

# Restore database
kubectl exec -n $NAMESPACE $PRIMARY_POD -- \
  pg_restore -U reflectai_user -d reflectai \
  --clean --if-exists --verbose \
  /tmp/restore.dump

echo "Database restore completed"
```

### Application State Backup

#### Configuration Backup
```bash
#!/bin/bash
# scripts/backup-config.sh

NAMESPACE="reflectai"
BACKUP_DIR="/backups/kubernetes"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup all Kubernetes resources
kubectl get all,configmaps,secrets,ingress,pvc,pv \
  -n $NAMESPACE -o yaml > \
  $BACKUP_DIR/k8s_resources_$TIMESTAMP.yaml

# Backup custom resources
kubectl get postgresql,rediscluster,jetstream \
  -n $NAMESPACE -o yaml > \
  $BACKUP_DIR/custom_resources_$TIMESTAMP.yaml

echo "Configuration backup completed"
```

## Scaling Operations

### Manual Scaling

#### Scale Application Services
```bash
# Scale core application
kubectl scale deployment reflectai-core --replicas=5 -n reflectai

# Scale specific services
kubectl scale deployment slack-gateway --replicas=3 -n reflectai
kubectl scale deployment agent-orchestrator --replicas=4 -n reflectai

# Verify scaling
kubectl get deployments -n reflectai
```

#### Scale Infrastructure Components
```bash
# Scale PostgreSQL cluster (requires operator support)
kubectl patch postgresql postgres-cluster -n reflectai \
  --type='merge' -p='{"spec":{"instances":5}}'

# Scale Redis cluster
kubectl patch rediscluster redis-cluster -n reflectai \
  --type='merge' -p='{"spec":{"clusterSize":8}}'

# Scale NATS cluster
kubectl scale statefulset nats --replicas=5 -n reflectai
```

### Auto-scaling Configuration

#### HPA Tuning
```yaml
# Update HPA thresholds
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: reflectai-hpa
  namespace: reflectai
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reflectai-core
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60  # Lower threshold for faster scaling
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: nats_consumer_lag
      target:
        type: AverageValue
        averageValue: "100"  # Scale based on message queue depth
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

## Performance Optimization

### Database Optimization

#### Query Performance Analysis
```sql
-- Check slow queries
SELECT query, mean_exec_time, calls, total_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 1000
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'reflectai'
ORDER BY n_distinct DESC;

-- Check table sizes
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'reflectai'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### Database Maintenance
```bash
# Run VACUUM and ANALYZE
kubectl exec -n reflectai postgres-cluster-1 -- \
  psql -U reflectai_user -d reflectai -c "VACUUM ANALYZE;"

# Reindex tables
kubectl exec -n reflectai postgres-cluster-1 -- \
  psql -U reflectai_user -d reflectai -c "REINDEX DATABASE reflectai;"

# Update statistics
kubectl exec -n reflectai postgres-cluster-1 -- \
  psql -U reflectai_user -d reflectai -c "ANALYZE;"
```

### Cache Optimization

#### Redis Performance Tuning
```bash
# Check Redis memory usage
kubectl exec -n reflectai redis-cluster-0 -- redis-cli info memory

# Check cache hit rates
kubectl exec -n reflectai redis-cluster-0 -- redis-cli info stats | grep hit

# Monitor slow queries
kubectl exec -n reflectai redis-cluster-0 -- redis-cli slowlog get 10

# Optimize memory usage
kubectl exec -n reflectai redis-cluster-0 -- redis-cli config set maxmemory-policy allkeys-lru
```

### NATS Performance Tuning

#### JetStream Optimization
```bash
# Check stream status
kubectl exec -n reflectai nats-0 -- nats stream info USER_ACTIVITIES

# Monitor consumer lag
kubectl exec -n reflectai nats-0 -- nats consumer info USER_ACTIVITIES user_activity_processor

# Optimize stream configuration
kubectl exec -n reflectai nats-0 -- nats stream edit USER_ACTIVITIES \
  --max-msgs=1000000 \
  --max-bytes=10GB \
  --max-age=720h
```

## Security Operations

### Certificate Management

#### SSL Certificate Renewal
```bash
# Check certificate status
kubectl get certificates -n reflectai

# Force certificate renewal
kubectl delete certificate reflectai-tls -n reflectai
kubectl apply -f infrastructure/certificates.yaml

# Verify certificate
kubectl describe certificate reflectai-tls -n reflectai
```

### Secret Rotation

#### Rotate Database Passwords
```bash
#!/bin/bash
# scripts/rotate-db-password.sh

NEW_PASSWORD=$(openssl rand -base64 32)
NAMESPACE="reflectai"

# Update secret
kubectl patch secret postgres-credentials -n $NAMESPACE \
  --type='json' \
  -p='[{"op": "replace", "path": "/data/password", "value": "'$(echo -n $NEW_PASSWORD | base64)'"}]'

# Update PostgreSQL user password
PRIMARY_POD=$(kubectl get pods -n $NAMESPACE -l postgresql=primary -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n $NAMESPACE $PRIMARY_POD -- \
  psql -U postgres -c "ALTER USER reflectai_user PASSWORD '$NEW_PASSWORD';"

# Restart applications to pick up new password
kubectl rollout restart deployment/reflectai-core -n $NAMESPACE

echo "Database password rotated successfully"
```

## Monitoring and Alerting

### Grafana Dashboard Management

#### Import Custom Dashboards
```bash
# Import ReflectAI dashboard
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -d @dashboards/reflectai-overview.json \
  http://grafana.reflectai.company.com/api/dashboards/db
```

### Alert Configuration

#### Prometheus Alert Rules
```yaml
# Custom alert rules for ReflectAI
groups:
- name: reflectai.business
  rules:
  - alert: HighMultiAgentFailureRate
    expr: |
      (
        sum(rate(reflectai_agent_executions_total{success="false"}[5m])) /
        sum(rate(reflectai_agent_executions_total[5m]))
      ) > 0.15
    for: 5m
    labels:
      severity: critical
      service: reflectai
    annotations:
      summary: "High multi-agent failure rate"
      description: "Multi-agent failure rate is {{ $value | humanizePercentage }}"
      runbook_url: "https://docs.reflectai.company.com/runbooks/multi-agent-failures"

  - alert: LLMTokenExhaustion
    expr: |
      sum(increase(reflectai_llm_tokens_total[1h])) > 500000
    for: 10m
    labels:
      severity: warning
      service: reflectai
    annotations:
      summary: "High LLM token usage"
      description: "LLM token usage is {{ $value }} tokens/hour"

  - alert: SlackEventBacklog
    expr: |
      nats_jetstream_consumer_num_pending{stream="SLACK_EVENTS"} > 1000
    for: 5m
    labels:
      severity: warning
      service: reflectai
    annotations:
      summary: "Slack event processing backlog"
      description: "{{ $value }} Slack events pending processing"
```

## Troubleshooting Runbooks

### Multi-Agent Execution Failures

#### Diagnosis Steps
1. **Check agent logs**:
   ```bash
   kubectl logs -l app=agent-orchestrator -n reflectai | grep -i "multi.agent"
   ```

2. **Verify LLM connectivity**:
   ```bash
   kubectl exec -n reflectai deployment/agent-orchestrator -- \
     curl -f $LLM_API_BASE_URL/health
   ```

3. **Check CrewAI configuration**:
   ```bash
   kubectl logs -l app=agent-orchestrator -n reflectai | grep -i "crew"
   ```

#### Resolution Steps
1. **Restart agent orchestrator**:
   ```bash
   kubectl rollout restart deployment/agent-orchestrator -n reflectai
   ```

2. **Scale down and up**:
   ```bash
   kubectl scale deployment agent-orchestrator --replicas=0 -n reflectai
   kubectl scale deployment agent-orchestrator --replicas=3 -n reflectai
   ```

### Database Connection Issues

#### Diagnosis
```bash
# Check PostgreSQL cluster status
kubectl get postgresql postgres-cluster -n reflectai

# Check connection pool
kubectl exec -n reflectai postgres-cluster-1 -- \
  psql -U reflectai_user -d reflectai -c "SELECT * FROM pg_stat_activity;"

# Test connectivity from application
kubectl exec -n reflectai deployment/reflectai-core -- \
  pg_isready -h postgres-cluster -p 5432 -U reflectai_user
```

#### Resolution
```bash
# Restart PostgreSQL cluster
kubectl delete pod postgres-cluster-1 -n reflectai

# Clear connection pool
kubectl exec -n reflectai postgres-cluster-1 -- \
  psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='reflectai';"
```

This operations manual provides comprehensive guidance for day-to-day management, troubleshooting, and optimization of the ReflectAI Enterprise platform.
