/**
 * k8s/minio.ts
 * Deploys MinIO — on-prem S3-compatible object store.
 * Used for: PostgreSQL backups, context archival, artifact cold storage.
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

export function deployMinio(
  provider: k8s.Provider,
  env: string,
  namespaceDep: k8s.core.v1.Namespace,
): k8s.helm.v3.Release {
  const isProd = env === "prod";

  return new k8s.helm.v3.Release(
    resourceName("minio", env),
    {
      name:           "minio",
      chart:          "minio",
      repositoryOpts: { repo: "https://charts.min.io" },
      version:        "5.2.0",
      namespace:      NAMESPACES.data,
      values: {
        image: {
          repository: "harbor.ai.adports.ae/minio/minio",
          tag:        "RELEASE.2024-10-02T17-50-41Z",
        },
        mode: isProd ? "distributed" : "standalone",
        replicas: isProd ? 4 : 1,
        persistence: {
          enabled: true,
          size: isProd ? "200Gi" : "50Gi",
        },
        resources: {
          requests: { memory: isProd ? "1Gi" : "512Mi", cpu: "500m" },
          limits:   { memory: isProd ? "2Gi" : "1Gi",   cpu: "1" },
        },
        // Root credentials injected via Vault Agent — see Vault policy orbit-data
        // Set via: vault kv put secret/orbit/minio rootUser=admin rootPassword=<secret>
        existingSecret: "minio-root-creds",
        buckets: [
          { name: "ai-portal-pg-backups",   policy: "none", purge: false },
          { name: "ai-portal-artifacts",    policy: "none", purge: false },
          { name: "ai-portal-context-archive", policy: "none", purge: false },
        ],
        metrics: {
          serviceMonitor: {
            enabled: true,
            includeNode: true,
          },
        },
        podSecurityContext: {
          runAsUser: 1000,
          runAsGroup: 1000,
          fsGroup: 1000,
          runAsNonRoot: true,
        },
        containerSecurityContext: {
          allowPrivilegeEscalation: false,
        },
        ingress: {
          enabled: false,  // exposed via Kong ingress in kong.ts
        },
      },
    },
    { provider, dependsOn: [namespaceDep] }
  );
}
