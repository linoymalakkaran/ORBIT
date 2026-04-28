/**
 * stacks/aks/index.ts — FUTURE AKS TARGET (placeholder)
 *
 * This stack will provision an AKS cluster using @pulumi/azure-native.
 * All k8s/ resources are cluster-agnostic and will reuse unchanged.
 *
 * To activate:
 *   npm install @pulumi/azure-native
 *   Implement cluster provisioning here, export kubeconfig.
 *   Update Pulumi.dev.yaml / Pulumi.prod.yaml with Azure config.
 */
import * as pulumi from "@pulumi/pulumi";

export const status = pulumi.output("AKS stack not yet implemented — Tanzu is the active target.");
