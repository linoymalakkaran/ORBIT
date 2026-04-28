/**
 * k8s/postgres.ts
 * Deploys CloudNativePG operator + a Postgres HA cluster.
 * Creates three databases: ai_portal_core, ai_portal_keycloak, ai_portal_context.
 * Backups go to MinIO (S3-compatible) at bucket ai-portal-pg-backups.
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

export function deployPostgres(
  provider: k8s.Provider,
  env: string,
  namespaceDep: k8s.core.v1.Namespace,
  vaultDep: k8s.helm.v3.Release,
): { operator: k8s.helm.v3.Release; cluster: k8s.apiextensions.CustomResource } {
  const isProd = env === "prod";

  // 1. CloudNativePG operator
  const operator = new k8s.helm.v3.Release(
    resourceName("cnpg-operator", env),
    {
      name:           "cloudnative-pg",
      chart:          "cloudnative-pg",
      repositoryOpts: { repo: "https://cloudnative-pg.github.io/charts" },
      version:        "0.22.1",
      namespace:      NAMESPACES.data,
      values: {
        image: {
          repository: "harbor.ai.adports.ae/cloudnative-pg/cloudnative-pg",
          tag: "1.24.1",
        },
        resources: {
          requests: { cpu: "100m", memory: "200Mi" },
          limits:   { cpu: "500m", memory: "400Mi" },
        },
      },
      waitForJobs: true,
    },
    { provider, dependsOn: [namespaceDep, vaultDep] }
  );

  // 2. Postgres Cluster CR
  const cluster = new k8s.apiextensions.CustomResource(
    resourceName("pg-cluster", env),
    {
      apiVersion: "postgresql.cnpg.io/v1",
      kind: "Cluster",
      metadata: {
        name: `orbit-postgres-${env}`,
        namespace: NAMESPACES.data,
        labels: { "project": "orbit", env },
        annotations: {
          // Vault Agent — inject DB password into pods that need it
          "vault.hashicorp.com/agent-inject": "true",
          "vault.hashicorp.com/role": "postgres-reader",
          "vault.hashicorp.com/agent-inject-secret-pg-creds":
            "secret/data/orbit/postgres",
        },
      },
      spec: {
        instances: isProd ? 3 : 2,
        imageName: "harbor.ai.adports.ae/cloudnative-pg/postgresql:16.4",
        primaryUpdateStrategy: "unsupervised",
        postgresql: {
          parameters: {
            max_connections: isProd ? "300" : "100",
            shared_buffers: isProd ? "512MB" : "128MB",
            effective_cache_size: isProd ? "1536MB" : "384MB",
            log_min_duration_statement: "1000",
          },
        },
        bootstrap: {
          initdb: {
            database: "ai_portal_core",
            owner: "orbit_app",
            postInitSQL: [
              "CREATE DATABASE ai_portal_keycloak OWNER orbit_app;",
              "CREATE DATABASE ai_portal_context  OWNER orbit_app;",
              "CREATE EXTENSION IF NOT EXISTS pgcrypto;",
              "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";",
            ],
          },
        },
        backup: {
          barmanObjectStore: {
            destinationPath: "s3://ai-portal-pg-backups",
            endpointURL: `http://minio.${NAMESPACES.data}.svc.cluster.local:9000`,
            s3Credentials: {
              accessKeyId: {
                name: "minio-s3-creds",
                key: "ACCESS_KEY_ID",
              },
              secretAccessKey: {
                name: "minio-s3-creds",
                key: "ACCESS_SECRET_KEY",
              },
            },
            wal: { compression: "gzip" },
            data: { compression: "gzip" },
          },
          retentionPolicy: "30d",
        },
        storage: {
          size: isProd ? "100Gi" : "20Gi",
        },
        resources: {
          requests: { memory: isProd ? "1Gi" : "256Mi", cpu: isProd ? "500m" : "250m" },
          limits:   { memory: isProd ? "2Gi" : "512Mi", cpu: isProd ? "1"    : "500m" },
        },
        monitoring: {
          enablePodMonitor: true,
        },
      },
    },
    { provider, dependsOn: [operator] }
  );

  return { operator, cluster };
}
