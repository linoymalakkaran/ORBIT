import * as pulumi from "@pulumi/pulumi";

/**
 * IPlatformProvider — abstraction interface for cluster provisioning.
 * Implemented by:
 *   - TanzuProvider  (stacks/tanzu/cluster.ts)
 *   - AksProvider    (stacks/aks/cluster.ts)   ← future
 *
 * All K8s resources in k8s/ are cluster-agnostic; they only consume
 * the outputs of this interface via Pulumi StackReference.
 */
export interface IPlatformProvider {
  /** Raw kubeconfig YAML for the provisioned workload cluster. */
  kubeconfig: pulumi.Output<string>;
  /** Kubernetes API server endpoint. */
  clusterEndpoint: pulumi.Output<string>;
  /** The cluster name / identifier (for labelling). */
  clusterName: pulumi.Output<string>;
}

/**
 * Standard tags / labels applied to every resource.
 */
export function commonTags(env: string, phase: string): Record<string, string> {
  return {
    project: "orbit",
    "managed-by": "pulumi",
    env,
    phase,
  };
}

/**
 * Canonical resource naming: adports-ai-{component}-{env}
 */
export function resourceName(component: string, env: string): string {
  return `adports-ai-${component}-${env}`;
}

/**
 * Standard namespace names used across all stacks.
 */
export const NAMESPACES = {
  system:        "ai-portal-system",
  core:          "ai-portal-core",
  data:          "ai-portal-data",
  agents:        "ai-portal-agents",
  vault:         "ai-portal-vault",
  keycloak:      "ai-portal-keycloak",
  observability: "ai-portal-observability",
} as const;
