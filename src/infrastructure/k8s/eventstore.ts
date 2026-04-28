/**
 * k8s/eventstore.ts
 * Deploys EventStoreDB — the immutable Pipeline Ledger backbone.
 * Dev: single node. Prod: 3-node cluster with gossip.
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

export function deployEventStore(
  provider: k8s.Provider,
  env: string,
  namespaceDep: k8s.core.v1.Namespace,
): k8s.helm.v3.Release {
  const isProd = env === "prod";

  return new k8s.helm.v3.Release(
    resourceName("eventstore", env),
    {
      name:           "eventstore",
      chart:          "eventstore",
      repositoryOpts: { repo: "https://eventstore.github.io/EventStore.Charts" },
      version:        "0.4.3",
      namespace:      NAMESPACES.data,
      values: {
        image: {
          repository: "harbor.ai.adports.ae/eventstore/eventstore",
          tag:        "24.10.1-bookworm-slim",
        },
        clusterSize: isProd ? 3 : 1,
        eventStoreConfig: {
          EVENTSTORE_INSECURE:              isProd ? "false" : "true",
          EVENTSTORE_ENABLE_EXTERNAL_TCP:   "false",
          EVENTSTORE_ENABLE_ATOM_PUB_OVER_HTTP: "false",
          EVENTSTORE_MEM_DB:                "false",
          EVENTSTORE_RUN_PROJECTIONS:       "System",
          EVENTSTORE_MAX_APPEND_SIZE:       "104857600",  // 100 MB
        },
        persistence: {
          enabled: true,
          size:    isProd ? "50Gi" : "10Gi",
        },
        resources: {
          requests: { memory: isProd ? "1Gi" : "512Mi", cpu: "500m" },
          limits:   { memory: isProd ? "2Gi" : "1Gi",   cpu: "1" },
        },
        podSecurityContext: {
          runAsUser: 1000,
          fsGroup:   1000,
          runAsNonRoot: true,
        },
        containerSecurityContext: {
          allowPrivilegeEscalation: false,
          readOnlyRootFilesystem: false,  // EventStoreDB writes data dirs
        },
        metrics: {
          serviceMonitor: { enabled: true },
        },
      },
    },
    { provider, dependsOn: [namespaceDep] }
  );
}
