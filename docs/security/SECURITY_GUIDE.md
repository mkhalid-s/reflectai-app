# Security Implementation Guide

## Security Architecture Overview

ReflectAI implements defense-in-depth security with multiple layers:
- **Network Security**: Zero-trust networking with Istio service mesh
- **Authentication**: OAuth2/OIDC enterprise integration
- **Authorization**: RBAC and fine-grained access controls
- **Secrets Management**: HashiCorp Vault for dynamic secrets
- **Data Protection**: Encryption at rest and in transit
- **Container Security**: Pod security standards and image scanning

## Network Security

### Istio Service Mesh Configuration

```yaml
# Zero-trust networking with mTLS
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: reflectai
spec:
  mtls:
    mode: STRICT

---
# Authorization policies
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: reflectai-authz
  namespace: reflectai
spec:
  selector:
    matchLabels:
      app: reflectai-core
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/istio-system/sa/istio-ingressgateway-service-account"]
  - to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/v1/*", "/health", "/metrics"]
```

### Network Policies

```yaml
# Kubernetes network policies for microsegmentation
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: reflectai-network-policy
  namespace: reflectai
spec:
  podSelector:
    matchLabels:
      app: reflectai-core
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: istio-system
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres-cluster
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis-cluster
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app: nats
    ports:
    - protocol: TCP
      port: 4222
```

## Authentication and Authorization

### OAuth2/OIDC Integration

```python
# Enterprise OAuth2 provider integration
class EnterpriseOAuthProvider:
    def __init__(self):
        self.client_id = os.getenv("OAUTH_CLIENT_ID")
        self.client_secret = os.getenv("OAUTH_CLIENT_SECRET")
        self.token_url = os.getenv("OAUTH_TOKEN_URL")
        self.jwks_url = os.getenv("OAUTH_JWKS_URL")

    async def validate_token(self, token: str) -> Optional[TokenPayload]:
        """Validate JWT token with JWKS"""
        try:
            # Get signing key from JWKS
            jwks_client = PyJWKClient(self.jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            # Decode and validate token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=os.getenv("OAUTH_ISSUER")
            )

            return TokenPayload(**payload)

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    async def get_service_token(self, scopes: List[str]) -> str:
        """Get service-to-service token"""
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": " ".join(scopes)
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    return token_data["access_token"]
                else:
                    raise AuthenticationError("Failed to get service token")
```

### RBAC Implementation

```yaml
# Kubernetes RBAC for fine-grained access control
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: reflectai
  name: reflectai-operator
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: ["postgresql.cnpg.io"]
  resources: ["clusters", "backups"]
  verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: reflectai-operator-binding
  namespace: reflectai
subjects:
- kind: ServiceAccount
  name: reflectai-service-account
  namespace: reflectai
roleRef:
  kind: Role
  name: reflectai-operator
  apiGroup: rbac.authorization.k8s.io
```

## Secrets Management

### HashiCorp Vault Integration

```python
# Vault client for dynamic secrets
class VaultSecretsManager:
    def __init__(self):
        self.vault_url = os.getenv("VAULT_URL", "https://vault.company.com")
        self.vault_token = None
        self.client = hvac.Client(url=self.vault_url)

    async def authenticate(self):
        """Authenticate with Vault using Kubernetes service account"""
        # Read service account token
        with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
            jwt_token = f.read()

        # Authenticate with Vault
        auth_response = self.client.auth.kubernetes.login(
            role="reflectai-service",
            jwt=jwt_token
        )

        self.vault_token = auth_response["auth"]["client_token"]
        self.client.token = self.vault_token

    async def get_database_credentials(self) -> Dict[str, str]:
        """Get dynamic database credentials"""
        response = self.client.secrets.database.generate_credentials(
            name="reflectai-db-role"
        )

        return {
            "username": response["data"]["username"],
            "password": response["data"]["password"]
        }

    async def get_llm_credentials(self) -> Dict[str, str]:
        """Get LLM API credentials"""
        response = self.client.secrets.kv.v2.read_secret_version(
            path="reflectai/llm-credentials"
        )

        return response["data"]["data"]

    async def rotate_secret(self, path: str):
        """Trigger secret rotation"""
        self.client.secrets.kv.v2.delete_metadata_and_all_versions(path=path)
        # Trigger regeneration through external process
```

### Secret Rotation Automation

```bash
#!/bin/bash
# scripts/rotate-secrets.sh

set -e

NAMESPACE="reflectai"
VAULT_ADDR="https://vault.company.com"

echo "Starting secret rotation..."

# Rotate database credentials
echo "Rotating database credentials..."
NEW_DB_CREDS=$(vault write -format=json database/creds/reflectai-role)
DB_USERNAME=$(echo $NEW_DB_CREDS | jq -r '.data.username')
DB_PASSWORD=$(echo $NEW_DB_CREDS | jq -r '.data.password')

# Update Kubernetes secret
kubectl patch secret postgres-credentials -n $NAMESPACE \
  --type='json' \
  -p='[
    {"op": "replace", "path": "/data/username", "value": "'$(echo -n $DB_USERNAME | base64)'"},
    {"op": "replace", "path": "/data/password", "value": "'$(echo -n $DB_PASSWORD | base64)'"}
  ]'

# Rotate LLM API credentials
echo "Rotating LLM credentials..."
vault kv put secret/reflectai/llm-credentials \
  api_key="$(openssl rand -hex 32)" \
  client_secret="$(openssl rand -hex 32)"

# Restart applications to pick up new secrets
kubectl rollout restart deployment/reflectai-core -n $NAMESPACE
kubectl rollout restart deployment/agent-orchestrator -n $NAMESPACE

echo "Secret rotation completed successfully"
```

## Container Security

### Pod Security Standards

```yaml
# Pod Security Policy enforcement
apiVersion: v1
kind: Namespace
metadata:
  name: reflectai
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted

---
# Secure pod template
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reflectai-core
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: reflectai-core
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 1000
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /app/cache
      volumes:
      - name: tmp
        emptyDir: {}
      - name: cache
        emptyDir: {}
```

### Image Security Scanning

```yaml
# Trivy security scanner
apiVersion: batch/v1
kind: CronJob
metadata:
  name: image-security-scan
  namespace: reflectai
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: trivy
            image: aquasec/trivy:latest
            command:
            - /bin/sh
            - -c
            - |
              trivy image --format json --output /tmp/scan-results.json reflectai/core:latest
              trivy image --format json --output /tmp/scan-results-gateway.json reflectai/slack-gateway:latest
              # Upload results to security dashboard
              curl -X POST -H "Content-Type: application/json" \
                -d @/tmp/scan-results.json \
                https://security-dashboard.company.com/api/scan-results
            volumeMounts:
            - name: scan-results
              mountPath: /tmp
          volumes:
          - name: scan-results
            emptyDir: {}
          restartPolicy: OnFailure
```

## Data Protection

### Encryption at Rest

```yaml
# PostgreSQL with encryption
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster
spec:
  postgresql:
    parameters:
      # Enable encryption
      ssl: "on"
      ssl_cert_file: "/etc/ssl/certs/server.crt"
      ssl_key_file: "/etc/ssl/private/server.key"
      ssl_ca_file: "/etc/ssl/certs/ca.crt"

      # Transparent Data Encryption
      shared_preload_libraries: "pg_tde"

  storage:
    storageClass: encrypted-ssd  # Use encrypted storage class
```

### Encryption in Transit

```yaml
# TLS configuration for all services
apiVersion: v1
kind: Secret
metadata:
  name: reflectai-tls
  namespace: reflectai
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-certificate>
  tls.key: <base64-encoded-private-key>

---
# Ingress with TLS termination
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: reflectai-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - reflectai.company.com
    secretName: reflectai-tls
```

## Compliance and Auditing

### Audit Logging

```python
# Comprehensive audit logging
class AuditLogger:
    def __init__(self):
        self.logger = get_logger("audit")

    def log_user_action(self, user_id: str, action: str, resource: str,
                       result: str, metadata: Dict[str, Any] = None):
        """Log user actions for compliance"""

        audit_event = {
            "event_type": "user_action",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "result": result,
            "metadata": metadata or {},
            "source_ip": self.get_source_ip(),
            "user_agent": self.get_user_agent(),
            "session_id": self.get_session_id()
        }

        self.logger.info("User action audit", extra=audit_event)

    def log_system_event(self, event_type: str, component: str,
                        details: Dict[str, Any]):
        """Log system events"""

        system_event = {
            "event_type": "system_event",
            "timestamp": datetime.utcnow().isoformat(),
            "component": component,
            "event_category": event_type,
            "details": details
        }

        self.logger.info("System event audit", extra=system_event)

    def log_data_access(self, user_id: str, data_type: str,
                       operation: str, record_count: int):
        """Log data access for privacy compliance"""

        data_event = {
            "event_type": "data_access",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "data_type": data_type,
            "operation": operation,
            "record_count": record_count,
            "compliance_category": "data_processing"
        }

        self.logger.info("Data access audit", extra=data_event)
```

### Security Monitoring

```yaml
# Falco security monitoring rules
- rule: Unauthorized Process in Container
  desc: Detect unauthorized processes in ReflectAI containers
  condition: >
    spawned_process and
    container.image.repository contains "reflectai" and
    not proc.name in (python, uvicorn, gunicorn, sh, bash)
  output: >
    Unauthorized process in ReflectAI container
    (user=%user.name command=%proc.cmdline container=%container.name)
  priority: WARNING

- rule: Sensitive File Access
  desc: Detect access to sensitive files
  condition: >
    open_read and
    container.image.repository contains "reflectai" and
    (fd.name contains "/etc/passwd" or
     fd.name contains "/etc/shadow" or
     fd.name contains "id_rsa")
  output: >
    Sensitive file accessed in ReflectAI container
    (file=%fd.name container=%container.name)
  priority: CRITICAL
```

This security implementation provides comprehensive protection for ReflectAI Enterprise with industry-standard security practices and compliance capabilities.
