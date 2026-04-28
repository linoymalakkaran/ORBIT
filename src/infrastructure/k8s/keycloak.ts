/**
 * k8s/keycloak.ts
 * Deploys Keycloak 25 and seeds the ai-portal realm via a Job.
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

export function deployKeycloak(
  provider: k8s.Provider,
  env: string,
  domain: string,
  namespaceDep: k8s.core.v1.Namespace,
  postgresDep: k8s.apiextensions.CustomResource,
): k8s.helm.v3.Release {
  const isProd = env === "prod";

  return new k8s.helm.v3.Release(
    resourceName("keycloak", env),
    {
      name:           "keycloak",
      chart:          "keycloak",
      repositoryOpts: { repo: "https://charts.bitnami.com/bitnami" },
      version:        "22.2.4",
      namespace:      NAMESPACES.keycloak,
      values: {
        image: {
          registry:   "harbor.ai.adports.ae",
          repository: "bitnami/keycloak",
          tag:        "25.0.6",
        },
        auth: {
          // Admin credentials fetched from Vault via init container
          existingSecret: "keycloak-admin-creds",
          passwordSecretKey: "admin-password",
        },
        replicaCount: isProd ? 3 : 1,
        extraEnvVars: [
          { name: "KC_HOSTNAME",          value: `auth.${domain}` },
          { name: "KC_HOSTNAME_STRICT",   value: "true" },
          { name: "KC_PROXY",             value: "edge" },
          { name: "KC_DB",                value: "postgres" },
          { name: "KC_DB_URL",            value: `jdbc:postgresql://orbit-postgres-${env}-rw.${NAMESPACES.data}.svc.cluster.local:5432/ai_portal_keycloak` },
          { name: "KC_DB_USERNAME",       value: "orbit_app" },
          { name: "KC_FEATURES",          value: "token-exchange,fine-grained-authz" },
          { name: "KC_LOG_LEVEL",         value: "INFO" },
          { name: "JAVA_OPTS_APPEND",     value: "-Djgroups.dns.query=keycloak-headless" },
        ],
        extraEnvVarsSecret: "keycloak-db-creds",  // KC_DB_PASSWORD
        resources: {
          requests: { memory: isProd ? "1Gi" : "512Mi", cpu: "500m" },
          limits:   { memory: isProd ? "2Gi" : "1Gi",   cpu: "1" },
        },
        livenessProbe: {
          httpGet: { path: "/health/live",  port: "http", scheme: "HTTP" },
          initialDelaySeconds: 60,
          periodSeconds: 10,
        },
        readinessProbe: {
          httpGet: { path: "/health/ready", port: "http", scheme: "HTTP" },
          initialDelaySeconds: 30,
          periodSeconds: 10,
        },
        service: {
          type: "ClusterIP",
        },
        podSecurityContext: {
          runAsUser: 1000,
          runAsNonRoot: true,
          fsGroup: 1000,
        },
        containerSecurityContext: {
          allowPrivilegeEscalation: false,
          readOnlyRootFilesystem: false,
        },
        metrics: {
          enabled: true,
          serviceMonitor: { enabled: true },
        },
      },
    },
    { provider, dependsOn: [namespaceDep, postgresDep] }
  );
}
