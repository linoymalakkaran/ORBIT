/**
 * k8s/network-policies.ts
 * Default-deny-all NetworkPolicy for every namespace.
 * Explicit allow rules for cross-namespace communication.
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES } from "../shared/platform";

function denyAll(ns: string, provider: k8s.Provider): k8s.networking.v1.NetworkPolicy {
  return new k8s.networking.v1.NetworkPolicy(`netpol-deny-all-${ns}`, {
    metadata: { name: "deny-all", namespace: ns, labels: { "project": "orbit" } },
    spec: {
      podSelector: {},   // match ALL pods in namespace
      policyTypes: ["Ingress", "Egress"],
      // No ingress / egress rules = deny everything
    },
  }, { provider });
}

function allowDnsEgress(ns: string, provider: k8s.Provider): k8s.networking.v1.NetworkPolicy {
  return new k8s.networking.v1.NetworkPolicy(`netpol-allow-dns-${ns}`, {
    metadata: { name: "allow-dns-egress", namespace: ns, labels: { "project": "orbit" } },
    spec: {
      podSelector: {},
      policyTypes: ["Egress"],
      egress: [{
        ports: [
          { port: 53, protocol: "UDP" },
          { port: 53, protocol: "TCP" },
        ],
      }],
    },
  }, { provider });
}

export function createNetworkPolicies(provider: k8s.Provider): void {
  const namespaces = Object.values(NAMESPACES);

  namespaces.forEach(ns => {
    denyAll(ns, provider);
    allowDnsEgress(ns, provider);
  });

  // ai-portal-data: allow inbound from core, agents, observability
  new k8s.networking.v1.NetworkPolicy("netpol-data-ingress", {
    metadata: { name: "allow-app-to-data", namespace: NAMESPACES.data, labels: { "project": "orbit" } },
    spec: {
      podSelector: {},
      policyTypes: ["Ingress"],
      ingress: [{
        from: [
          { namespaceSelector: { matchLabels: { "kubernetes.io/metadata.name": NAMESPACES.core } } },
          { namespaceSelector: { matchLabels: { "kubernetes.io/metadata.name": NAMESPACES.agents } } },
          { namespaceSelector: { matchLabels: { "kubernetes.io/metadata.name": NAMESPACES.keycloak } } },
          { namespaceSelector: { matchLabels: { "kubernetes.io/metadata.name": NAMESPACES.observability } } },
        ],
      }],
    },
  }, { provider });

  // ai-portal-vault: allow inbound from ALL namespaces (injector pattern)
  new k8s.networking.v1.NetworkPolicy("netpol-vault-ingress", {
    metadata: { name: "allow-all-to-vault", namespace: NAMESPACES.vault, labels: { "project": "orbit" } },
    spec: {
      podSelector: {},
      policyTypes: ["Ingress"],
      ingress: [{ from: [{ namespaceSelector: {} }] }],
    },
  }, { provider });

  // ai-portal-system: allow inbound from ALL (system services need broad access)
  new k8s.networking.v1.NetworkPolicy("netpol-system-ingress", {
    metadata: { name: "allow-ingress-system", namespace: NAMESPACES.system, labels: { "project": "orbit" } },
    spec: {
      podSelector: {},
      policyTypes: ["Ingress"],
      ingress: [{ from: [{ namespaceSelector: {} }] }],
    },
  }, { provider });
}
