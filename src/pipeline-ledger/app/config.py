from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEDGER_", env_file=".env", extra="ignore")

    # EventStoreDB
    esdb_connection_string: str = "esdb://eventstore:2113?tls=false"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_events: str = "orbit.pipeline.events"
    kafka_consumer_group: str = "ledger-projector"

    # PostgreSQL (read model / index)
    pg_dsn: str = "postgresql+asyncpg://ledger:changeme@postgres:5432/orbit_ledger"

    # Keycloak OIDC
    keycloak_issuer: str = "https://auth.ai.adports.ae/realms/ai-portal"
    keycloak_audience: str = "portal-api"

    # OTEL
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_service_name: str = "pipeline-ledger"


settings = Settings()
