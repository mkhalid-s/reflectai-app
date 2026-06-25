# Monitoring & Observability

## OpenTelemetry Integration

### Comprehensive Observability Setup

ReflectAI implements the three pillars of observability using OpenTelemetry:
- **Traces**: Distributed request tracing across services
- **Metrics**: Business and system metrics collection
- **Logs**: Structured logging with correlation

### OpenTelemetry Collector Configuration

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  prometheus:
    config:
      scrape_configs:
      - job_name: 'reflectai-services'
        kubernetes_sd_configs:
        - role: pod
          namespaces:
            names: [reflectai]

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

  resource:
    attributes:
    - key: service.namespace
      value: reflectai
      action: upsert

  memory_limiter:
    limit_mib: 512

exporters:
  jaeger:
    endpoint: jaeger-collector:14250
    tls:
      insecure: true

  prometheus:
    endpoint: "0.0.0.0:8889"
    namespace: reflectai

  loki:
    endpoint: http://loki:3100/loki/api/v1/push

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [jaeger]

    metrics:
      receivers: [otlp, prometheus]
      processors: [memory_limiter, resource, batch]
      exporters: [prometheus]

    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [loki]
```

### Application Instrumentation

```python
# Comprehensive telemetry setup
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def setup_telemetry():
    # Resource identification
    resource = Resource.create({
        "service.name": os.getenv("SERVICE_NAME", "reflectai-core"),
        "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
        "service.namespace": "reflectai",
        "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        "k8s.cluster.name": os.getenv("CLUSTER_NAME", "reflectai-cluster"),
        "k8s.namespace.name": os.getenv("NAMESPACE", "reflectai"),
        "k8s.pod.name": os.getenv("POD_NAME", "unknown")
    })

    # Tracing setup
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)

    # OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_COLLECTOR_ENDPOINT", "http://otel-collector:4317"),
        insecure=True
    )

    span_processor = BatchSpanProcessor(otlp_exporter)
    trace_provider.add_span_processor(span_processor)

    # Auto-instrumentation
    FastAPIInstrumentor.instrument()
    SQLAlchemyInstrumentor.instrument()
    RedisInstrumentor.instrument()

    return trace.get_tracer(__name__)
```

## Custom Business Metrics

### Multi-Agent Performance Metrics

```python
class ReflectAIMetrics:
    def __init__(self):
        self.meter = metrics.get_meter(__name__)

        # Agent execution metrics
        self.agent_executions = self.meter.create_counter(
            "reflectai_agent_executions_total",
            description="Total agent executions"
        )

        self.agent_duration = self.meter.create_histogram(
            "reflectai_agent_execution_duration_seconds",
            description="Agent execution duration"
        )

        # Multi-agent crew metrics
        self.crew_executions = self.meter.create_counter(
            "reflectai_crew_executions_total",
            description="Total crew executions"
        )

        # LLM usage metrics
        self.llm_tokens = self.meter.create_counter(
            "reflectai_llm_tokens_total",
            description="LLM tokens consumed"
        )

        # Business metrics
        self.competency_analyses = self.meter.create_counter(
            "reflectai_competency_analyses_total",
            description="Competency analyses performed"
        )

    def record_agent_execution(self, agent_name: str, duration: float, success: bool):
        attributes = {
            "agent_name": agent_name,
            "success": str(success)
        }
        self.agent_executions.add(1, attributes)
        self.agent_duration.record(duration, attributes)
```

## Distributed Tracing

### Multi-Agent Tracing

```python
class MultiAgentTracer:
    def __init__(self):
        self.tracer = trace.get_tracer(__name__)

    @asynccontextmanager
    async def trace_crew_execution(self, crew_id: str, user_id: str):
        with self.tracer.start_as_current_span("crew_execution") as span:
            span.set_attribute("crew.id", crew_id)
            span.set_attribute("user.id", user_id)
            span.set_attribute("operation.type", "multi_agent_analysis")

            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_attribute("error.message", str(e))
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    @asynccontextmanager
    async def trace_agent_execution(self, agent_name: str, task_name: str):
        with self.tracer.start_as_current_span(f"agent_execution.{agent_name}") as span:
            span.set_attribute("agent.name", agent_name)
            span.set_attribute("agent.task", task_name)

            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_attribute("error.message", str(e))
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
```

## Grafana Dashboards

### Multi-Agent Performance Dashboard

```json
{
  "dashboard": {
    "title": "ReflectAI Multi-Agent Performance",
    "panels": [
      {
        "title": "Agent Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(reflectai_agent_executions_total{success=\"true\"}[5m])) by (agent_name) / sum(rate(reflectai_agent_executions_total[5m])) by (agent_name) * 100"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "yellow", "value": 90},
                {"color": "green", "value": 95}
              ]
            }
          }
        }
      },
      {
        "title": "Agent Execution Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(reflectai_agent_execution_duration_seconds_bucket[5m])) by (le, agent_name))",
            "legendFormat": "{{agent_name}} P95"
          }
        ]
      },
      {
        "title": "LLM Token Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(reflectai_llm_tokens_total[5m])) by (agent_name)",
            "legendFormat": "{{agent_name}}"
          }
        ]
      }
    ]
  }
}
```

## Health Monitoring

### Comprehensive Health Checks

```python
class HealthService:
    def __init__(self):
        self.health_checks = {
            "database": DatabaseHealthCheck(),
            "redis": RedisHealthCheck(),
            "nats": NATSHealthCheck(),
            "temporal": TemporalHealthCheck()
        }

    async def detailed_health_check(self):
        results = {}
        for name, checker in self.health_checks.items():
            try:
                results[name] = await checker.detailed_check()
            except Exception as e:
                results[name] = {"error": str(e), "healthy": False}

        return {
            "status": "detailed",
            "checks": results,
            "timestamp": time.time()
        }
```

## Alerting Rules

### Prometheus Alerts

```yaml
groups:
- name: reflectai.performance
  rules:
  - alert: HighMultiAgentFailureRate
    expr: sum(rate(reflectai_agent_executions_total{success="false"}[5m])) / sum(rate(reflectai_agent_executions_total[5m])) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High multi-agent failure rate"
      description: "Multi-agent failure rate is {{ $value | humanizePercentage }}"

  - alert: LLMTokenExhaustion
    expr: sum(rate(reflectai_llm_tokens_total[1h])) > 1000000
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High LLM token usage"
      description: "Token usage: {{ $value }} tokens/hour"
```

This observability setup provides complete visibility into ReflectAI's multi-agent operations with OpenTelemetry standards.
