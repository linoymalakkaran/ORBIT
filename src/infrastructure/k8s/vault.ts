/**
 * k8s/vault.ts
 * Deploys HashiCorp Vault via Helm.
 * Dev: single node (dev mode for quick bootstrap).
 * Prod: 3-node HA with Raft integrated storage.
 *
 * Post-deploy manual steps (see runbook):
 *   1. vault operator init  (save unseal keys + root token to safe offline storage)
 *   2. vault operator unseal  (3× with unseal keys)
 *   3. vault auth enable kubernetes
 *   4. vault secrets enable -path=secret kv-v2
 *   5. vault secrets enable pki  (for internal cert issuing)
 *   6. Seed initial secrets (LLM API keys, CI tokens, etc.)
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

export function deployVault(
  provider: k8s.Provider,
  env: string,
  namespaceDep: k8s.core.v1.Namespace,
): k8s.helm.v3.Release {
  const isProd = env === "prod";

  return new k8s.helm.v3.Release(
    resourceName("vault", env),
    {
      name:           "vault",
      chart:          "vault",
      repositoryOpts: { repo: "https://helm.releases.hashicorp.com" },
      version:        "0.28.1",
      namespace:      NAMESPACES.vault,
      values: {
        global: {
          tlsDisable: false,
        },
        server: {
          image: {
            repository: "harbor.ai.adports.ae/hashicorp/vault",
            tag: "1.17.3",
          },
          resources: {
            requests: { memory: "256Mi", cpu: "250m" },
            limits:   { memory: "512Mi", cpu: "500m" },
          },
          readinessProbe: {
            exec: { command: ["vault", "status", "-tls-skip-verify"] },
            initialDelaySeconds: 10,
            periodSeconds: 5,
          },
          livenessProbe: {
            exec: { command: ["vault", "status", "-tls-skip-verify"] },
            initialDelaySeconds: 60,
            periodSeconds: 10,
          },
          extraEnvironmentVars: {
            VAULT_CACERT: "/vault/userconfig/tls/ca.crt",
          },
          ha: {
            enabled: isProd,
            replicas: isProd ? 3 : 1,
            raft: {
              enabled: isProd,
              setNodeId: true,
            },
          },
          standalone: {
            enabled: !isProd,
            config: `
ui = true
listener "tcp" {
  address = "[::]:8200"
  cluster_address = "[::]:8201"
  tls_disable = "true"  # TLS terminated by Kong/ingress in dev
}
storage "raft" {
  path    = "/vault/data"
  node_id = "vault-0"
}
service_registration "kubernetes" {}
`,
          },
          dataStorage: {
            enabled: true,
            size: isProd ? "20Gi" : "10Gi",
            storageClass: null,  // use cluster default storage class
          },
          serviceAccount: {
            create: true,
            name: "vault",
            annotations: { "project": "orbit" },
          },
        },
        injector: {
          enabled: true,
          image: {
            repository: "harbor.ai.adports.ae/hashicorp/vault-k8s",
            tag: "1.4.2",
          },
          resources: {
            requests: { memory: "128Mi", cpu: "100m" },
            limits:   { memory: "256Mi", cpu: "250m" },
          },
        },
        ui: {
          enabled: true,
          serviceType: "ClusterIP",
        },
      },
    },
    { provider, dependsOn: [namespaceDep] }
  );
}
