/**
 * k8s/observability.ts
 * Deploys the full observability stack via Helm:
 *   - kube-prometheus-stack (Prometheus + Grafana + Alertmanager)
 *   - Grafana Loki + Promtail
 *   - Grafana Tempo (distributed tracing)
 *   - OpenTelemetry Collector
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

export function deployObservability(
  provider: k8s.Provider,
  env: string,
  domain: string,
  namespaceDep: k8s.core.v1.Namespace,
): {
  prometheus: k8s.helm.v3.Release;
  loki:       k8s.helm.v3.Release;
  tempo:      k8s.helm.v3.Release;
  otel:       k8s.helm.v3.Release;
} {
  const isProd = env === "prod";

  // 1. kube-prometheus-stack
  const prometheus = new k8s.helm.v3.Release(
    resourceName("prometheus-stack", env),
    {
      name:           "kube-prometheus-stack",
      chart:          "kube-prometheus-stack",
      repositoryOpts: { repo: "https://prometheus-community.github.io/helm-charts" },
      version:        "62.6.0",
      namespace:      NAMESPACES.observability,
      values: {
        global: {
          imageRegistry: "harbor.ai.adports.ae",
        },
        grafana: {
          enabled: true,
          adminUser: "admin",
          // password injected via Vault agent
          persistence: { enabled: true, size: "5Gi" },
          ingress: { enabled: false },
          grafana_ini: {
            server:   { root_url: `https://grafana.${domain}` },
            auth_generic_oauth: {
              enabled:              true,
              name:                 "Keycloak",
              allow_sign_up:        true,
              client_id:            "grafana",
              scopes:               "openid profile email",
              auth_url:             `https://auth.${domain}/realms/ai-portal/protocol/openid-connect/auth`,
              token_url:            `https://auth.${domain}/realms/ai-portal/protocol/openid-connect/token`,
              api_url:              `https://auth.${domain}/realms/ai-portal/protocol/openid-connect/userinfo`,
              role_attribute_path:  "contains(realm_access.roles[*], 'portal:admin') && 'Admin' || 'Viewer'",
            },
          },
          resources: {
            requests: { cpu: "100m", memory: "256Mi" },
            limits:   { cpu: "500m", memory: "512Mi" },
          },
          sidecar: {
            dashboards: { enabled: true, searchNamespace: "ALL" },
            datasources: { enabled: true },
          },
        },
        prometheus: {
          prometheusSpec: {
            retention: isProd ? "30d" : "7d",
            storageSpec: {
              volumeClaimTemplate: {
                spec: {
                  accessModes: ["ReadWriteOnce"],
                  resources: { requests: { storage: isProd ? "100Gi" : "20Gi" } },
                },
              },
            },
            resources: {
              requests: { cpu: "250m", memory: "512Mi" },
              limits:   { cpu: "1",    memory: isProd ? "4Gi" : "2Gi" },
            },
          },
        },
        alertmanager: {
          alertmanagerSpec: {
            resources: {
              requests: { cpu: "50m",  memory: "128Mi" },
              limits:   { cpu: "100m", memory: "256Mi" },
            },
          },
        },
      },
    },
    { provider, dependsOn: [namespaceDep] }
  );

  // 2. Loki
  const loki = new k8s.helm.v3.Release(
    resourceName("loki", env),
    {
      name:           "loki",
      chart:          "loki-stack",
      repositoryOpts: { repo: "https://grafana.github.io/helm-charts" },
      version:        "2.10.2",
      namespace:      NAMESPACES.observability,
      values: {
        loki: {
          enabled: true,
          image: {
            repository: "harbor.ai.adports.ae/grafana/loki",
            tag:        "3.2.0",
          },
          persistence: {
            enabled: true,
            size:    isProd ? "50Gi" : "10Gi",
          },
          config: {
            table_manager: { retention_deletes_enabled: true, retention_period: isProd ? "720h" : "168h" },
          },
          resources: {
            requests: { cpu: "100m", memory: "256Mi" },
            limits:   { cpu: "500m", memory: isProd ? "2Gi" : "1Gi" },
          },
        },
        promtail: {
          enabled: true,
          image: {
            repository: "harbor.ai.adports.ae/grafana/promtail",
            tag:        "3.2.0",
          },
          resources: {
            requests: { cpu: "50m",  memory: "64Mi" },
            limits:   { cpu: "100m", memory: "128Mi" },
          },
        },
      },
    },
    { provider, dependsOn: [prometheus] }
  );

  // 3. Tempo
  const tempo = new k8s.helm.v3.Release(
    resourceName("tempo", env),
    {
      name:           "tempo",
      chart:          "tempo",
      repositoryOpts: { repo: "https://grafana.github.io/helm-charts" },
      version:        "1.10.3",
      namespace:      NAMESPACES.observability,
      values: {
        image: {
          repository: "harbor.ai.adports.ae/grafana/tempo",
          tag:        "2.6.0",
        },
        tempo: {
          retention: isProd ? "720h" : "168h",
          storage: {
            trace: {
              backend: "local",
              local: { path: "/var/tempo/traces" },
            },
          },
          resources: {
            requests: { cpu: "100m", memory: "256Mi" },
            limits:   { cpu: "500m", memory: isProd ? "2Gi" : "1Gi" },
          },
        },
        persistence: {
          enabled: true,
          size:    isProd ? "50Gi" : "10Gi",
        },
      },
    },
    { provider, dependsOn: [prometheus] }
  );

  // 4. OpenTelemetry Collector
  const otel = new k8s.helm.v3.Release(
    resourceName("otel-collector", env),
    {
      name:           "otel-collector",
      chart:          "opentelemetry-collector",
      repositoryOpts: { repo: "https://open-telemetry.github.io/opentelemetry-helm-charts" },
      version:        "0.107.0",
      namespace:      NAMESPACES.observability,
      values: {
        image: {
          repository: "harbor.ai.adports.ae/otel/opentelemetry-collector-contrib",
          tag:        "0.107.0",
        },
        mode: "deployment",
        config: {
          receivers: {
            otlp: {
              protocols: {
                grpc: { endpoint: "0.0.0.0:4317" },
                http: { endpoint: "0.0.0.0:4318" },
              },
            },
          },
          processors: {
            batch:        {},
            memory_limiter: { check_interval: "5s", limit_mib: 400, spike_limit_mib: 100 },
          },
          exporters: {
            prometheusremotewrite: {
              endpoint: `http://kube-prometheus-stack-prometheus.${NAMESPACES.observability}.svc.cluster.local:9090/api/v1/write`,
            },
            loki: {
              endpoint: `http://loki.${NAMESPACES.observability}.svc.cluster.local:3100/loki/api/v1/push`,
            },
            otlp: {
              endpoint: `tempo.${NAMESPACES.observability}.svc.cluster.local:4317`,
              tls: { insecure: true },
            },
          },
          service: {
            pipelines: {
              traces:  { receivers: ["otlp"], processors: ["memory_limiter", "batch"], exporters: ["otlp"] },
              metrics: { receivers: ["otlp"], processors: ["memory_limiter", "batch"], exporters: ["prometheusremotewrite"] },
              logs:    { receivers: ["otlp"], processors: ["memory_limiter", "batch"], exporters: ["loki"] },
            },
          },
        },
        resources: {
          requests: { cpu: "100m", memory: "256Mi" },
          limits:   { cpu: "500m", memory: "512Mi" },
        },
      },
    },
    { provider, dependsOn: [prometheus, loki, tempo] }
  );

  return { prometheus, loki, tempo, otel };
}
