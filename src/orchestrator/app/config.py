from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORCH_", env_file=".env", extra="ignore")

    # LiteLLM gateway
    litellm_api_base: str = "http://litellm-gateway.ai-portal.svc:4000"
    litellm_api_key:  str = "changeme"
    default_model:    str = "gpt-4o-mini"

    # Temporal
    temporal_host: str = "temporal.ai-portal.svc:7233"
    temporal_namespace: str = "orbit"
    temporal_task_queue: str = "orbit-pipeline"

    # Redis (context)
    redis_url: str = "redis://orbit-redis-redis-cluster.ai-portal-data.svc:6379"

    # MCP Registry
    mcp_registry_url: str = "http://mcp-registry.ai-portal.svc:80"

    # Capability Fabric
    fabric_api_url: str = "http://capability-fabric.ai-portal.svc:80"

    # Pipeline Ledger
    ledger_api_url: str = "http://pipeline-ledger.ai-portal.svc:80"

    # Keycloak
    keycloak_issuer: str = "https://auth.ai.adports.ae/realms/ai-portal"
    keycloak_audience: str = "portal-api"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_events: str = "orbit.pipeline.events"

    # OTEL
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_service_name: str = "orchestrator"

    # G27: Intelligent LLM routing — per-project defaults (overridable per request)
    data_classification: str = "internal"   # public | internal | confidential | restricted
    task_sensitivity: str = "internal"      # public | internal | confidential | restricted
    sovereign_model: str = "llama3-70b-sovereign"


settings = Settings()
