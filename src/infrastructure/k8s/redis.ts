/**
 * k8s/redis.ts
 * Deploys Redis Cluster (3 masters + 3 replicas) via Bitnami Helm chart.
 * Key prefixes: portal:, context:, session:, cache:
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

export function deployRedis(
  provider: k8s.Provider,
  env: string,
  namespaceDep: k8s.core.v1.Namespace,
): k8s.helm.v3.Release {
  const isProd = env === "prod";

  return new k8s.helm.v3.Release(
    resourceName("redis", env),
    {
      name:           "redis",
      chart:          "redis-cluster",
      repositoryOpts: { repo: "https://charts.bitnami.com/bitnami" },
      version:        "11.0.6",
      namespace:      NAMESPACES.data,
      values: {
        image: {
          registry:   "harbor.ai.adports.ae",
          repository: "bitnami/redis-cluster",
          tag:        "7.2.6",
        },
        cluster: {
          nodes:    isProd ? 6 : 3,   // 3 masters + 3 replicas (prod); 3 masters (dev)
          replicas: isProd ? 1 : 0,
        },
        redis: {
          configmap: `
maxmemory-policy allkeys-lru
save 900 1
save 300 10
appendonly yes
appendfsync everysec
`,
          resources: {
            requests: { cpu: "250m", memory: "512Mi" },
            limits:   { cpu: "500m", memory: isProd ? "2Gi" : "1Gi" },
          },
        },
        persistence: {
          enabled: true,
          size: isProd ? "20Gi" : "5Gi",
        },
        metrics: {
          enabled: true,
          serviceMonitor: { enabled: true },
          resources: {
            requests: { cpu: "50m",  memory: "64Mi" },
            limits:   { cpu: "100m", memory: "128Mi" },
          },
        },
        podSecurityContext: {
          runAsUser: 1001,
          fsGroup:   1001,
        },
        containerSecurityContext: {
          runAsNonRoot:             true,
          readOnlyRootFilesystem:   false,  // Redis needs /data write access
          allowPrivilegeEscalation: false,
        },
      },
    },
    { provider, dependsOn: [namespaceDep] }
  );
}
