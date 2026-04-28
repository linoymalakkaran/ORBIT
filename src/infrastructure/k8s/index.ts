/**
 * k8s/index.ts — ORBIT Platform K8s Stack entry point
 *
 * DEPLOYMENT ORDER:
 *   1. Namespaces
 *   2. MetalLB  (needed before any LoadBalancer Service)
 *   3. cert-manager  (needed before TLS Ingresses)
 *   4. Vault  (needed before secrets-dependent workloads)
 *   5. MinIO  (needed before Postgres backups)
 *   6. Postgres  (needed before Keycloak)
 *   7. Redis
 *   8. Kafka
 *   9. EventStoreDB
 *  10. Keycloak
 *  11. Kong
 *  12. ArgoCD + app-of-apps  (ArgoCD then manages the rest via GitOps)
 *  13. Observability stack
 *  14. Network Policies
 *
 * HOW TO USE:
 *   pulumi stack select dev
 *   pulumi config set orbit-k8s-platform:kubeconfigPath "~/.kube/orbit-dev.yaml"
 *   pulumi config set orbit-k8s-platform:internalCaCert "<base64>" --secret
 *   pulumi config set orbit-k8s-platform:internalCaKey  "<base64>" --secret
 *   pulumi up
 */

import * as pulumi from "@pulumi/pulumi";
import * as k8s from "@pulumi/kubernetes";

import { createNamespaces }     from "./namespaces";
import { deployMetalLb }        from "./metallb";
import { deployCertManager }    from "./cert-manager";
import { deployVault }          from "./vault";
import { deployMinio }          from "./minio";
import { deployPostgres }       from "./postgres";
import { deployRedis }          from "./redis";
import { deployKafka }          from "./kafka";
import { deployEventStore }     from "./eventstore";
import { deployKeycloak }       from "./keycloak";
import { deployKong }           from "./kong";
import { deployArgoCD }         from "./argocd";
import { deployObservability }  from "./observability";
import { createNetworkPolicies } from "./network-policies";

// ─── Config ──────────────────────────────────────────────────────────────────
const cfg    = new pulumi.Config("orbit-k8s-platform");
const env    = cfg.require("env");
const domain = cfg.require("domain");
const metallbIpRange   = cfg.require("metallbIpRange");
const kubeconfigPath   = cfg.get("kubeconfigPath");

// CA cert and key are secrets — set via: pulumi config set --secret
const internalCaCert  = cfg.requireSecret("internalCaCert");
const internalCaKey   = cfg.requireSecret("internalCaKey");

// ─── K8s Provider (points at the TKG workload cluster) ───────────────────────
const provider = new k8s.Provider("orbit-k8s", {
  kubeconfig: kubeconfigPath,
  // If kubeconfigPath is not set, uses KUBECONFIG env var / default context
});

// ─── 1. Namespaces ────────────────────────────────────────────────────────────
const namespaces = createNamespaces(provider, env);
const nsSystem   = namespaces.find(n => n.metadata.name.apply(name => name === "ai-portal-system"))!;
const nsData     = namespaces.find(n => n.metadata.name.apply(name => name === "ai-portal-data"))!;
const nsVault    = namespaces.find(n => n.metadata.name.apply(name => name === "ai-portal-vault"))!;
const nsKeycloak = namespaces.find(n => n.metadata.name.apply(name => name === "ai-portal-keycloak"))!;
const nsObs      = namespaces.find(n => n.metadata.name.apply(name => name === "ai-portal-observability"))!;

// ─── 2. MetalLB ──────────────────────────────────────────────────────────────
const metallb = deployMetalLb(provider, env, metallbIpRange, nsSystem);

// ─── 3. cert-manager ─────────────────────────────────────────────────────────
const certManager = deployCertManager(provider, env, internalCaCert, internalCaKey, nsSystem);

// ─── 4. Vault ────────────────────────────────────────────────────────────────
const vault = deployVault(provider, env, nsVault);

// ─── 5. MinIO ────────────────────────────────────────────────────────────────
const minio = deployMinio(provider, env, nsData);

// ─── 6. Postgres ─────────────────────────────────────────────────────────────
const { operator: pgOperator, cluster: pgCluster } =
  deployPostgres(provider, env, nsData, vault);

// ─── 7. Redis ────────────────────────────────────────────────────────────────
const redis = deployRedis(provider, env, nsData);

// ─── 8. Kafka ────────────────────────────────────────────────────────────────
const { operator: kafkaOperator, cluster: kafkaCluster } =
  deployKafka(provider, env, nsData);

// ─── 9. EventStoreDB ─────────────────────────────────────────────────────────
const eventstore = deployEventStore(provider, env, nsData);

// ─── 10. Keycloak ─────────────────────────────────────────────────────────────
const keycloak = deployKeycloak(provider, env, domain, nsKeycloak, pgCluster);

// ─── 11. Kong ─────────────────────────────────────────────────────────────────
const kong = deployKong(provider, env, domain, nsSystem, metallb, certManager);

// ─── 12. ArgoCD ──────────────────────────────────────────────────────────────
const argocd = deployArgoCD(provider, env, nsSystem, vault);

// ─── 13. Observability ───────────────────────────────────────────────────────
const { prometheus, loki, tempo, otel } =
  deployObservability(provider, env, domain, nsObs);

// ─── 14. Network Policies ────────────────────────────────────────────────────
createNetworkPolicies(provider);

// ─── Stack Outputs ───────────────────────────────────────────────────────────
export const grafanaUrl    = `https://grafana.${domain}`;
export const keycloakUrl   = `https://auth.${domain}`;
export const argocdUrl     = `https://argocd.${domain}`;
export const vaultUrl      = `https://vault.${domain}`;
export const minioConsole  = `https://minio.${domain}`;
export const deployedEnv   = env;
