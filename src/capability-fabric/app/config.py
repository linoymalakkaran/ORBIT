from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FABRIC_", env_file=".env", extra="ignore")

    pg_dsn: str = "postgresql+asyncpg://fabric:changeme@postgres:5432/orbit_fabric"
    minio_endpoint: str = "minio.ai-portal-data.svc.cluster.local:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme"
    minio_bucket_skills: str = "orbit-skills"
    keycloak_issuer: str = "https://auth.ai.adports.ae/realms/ai-portal"
    keycloak_audience: str = "portal-api"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_service_name: str = "capability-fabric"


settings = Settings()
