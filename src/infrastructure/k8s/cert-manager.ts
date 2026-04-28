/**
 * k8s/cert-manager.ts
 * Deploys cert-manager and configures a ClusterIssuer backed by the AD Ports
 * internal CA. All ORBIT services get TLS certificates from this issuer.
 */
import * as pulumi from "@pulumi/pulumi";
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

export function deployCertManager(
  provider: k8s.Provider,
  env: string,
  internalCaCert: pulumi.Output<string>,   // base64-encoded PEM CA cert
  internalCaKey: pulumi.Output<string>,    // base64-encoded PEM CA private key (secret)
  namespaceDep: k8s.core.v1.Namespace,
): k8s.helm.v3.Release {
  const chart = new k8s.helm.v3.Release(
    resourceName("cert-manager", env),
    {
      name:           "cert-manager",
      chart:          "cert-manager",
      repositoryOpts: { repo: "https://charts.jetstack.io" },
      version:        "1.16.2",
      namespace:      NAMESPACES.system,
      values: {
        installCRDs: true,
        global: {
          leaderElection: { namespace: NAMESPACES.system },
        },
        resources: {
          requests: { cpu: "100m", memory: "128Mi" },
          limits:   { cpu: "500m", memory: "256Mi" },
        },
        webhook: {
          resources: {
            requests: { cpu: "50m",  memory: "64Mi" },
            limits:   { cpu: "100m", memory: "128Mi" },
          },
        },
        cainjector: {
          resources: {
            requests: { cpu: "50m",  memory: "128Mi" },
            limits:   { cpu: "200m", memory: "256Mi" },
          },
        },
      },
      waitForJobs: true,
    },
    { provider, dependsOn: [namespaceDep] }
  );

  // Store the CA keypair in a K8s Secret (Vault will own the actual value;
  // cert-manager reads from this Secret to sign leaf certs)
  const caSecret = new k8s.core.v1.Secret(
    resourceName("adports-internal-ca", env),
    {
      metadata: {
        name:      "adports-internal-ca",
        namespace: NAMESPACES.system,
        labels:    { "project": "orbit", env },
      },
      type: "kubernetes.io/tls",
      data: {
        "tls.crt": internalCaCert,
        "tls.key": internalCaKey,
      },
    },
    { provider, dependsOn: [chart] }
  );

  // ClusterIssuer using the internal CA
  new k8s.apiextensions.CustomResource(
    resourceName("cluster-issuer", env),
    {
      apiVersion: "cert-manager.io/v1",
      kind: "ClusterIssuer",
      metadata: {
        name: "adports-internal-ca",
        labels: { "project": "orbit", env },
      },
      spec: {
        ca: { secretName: "adports-internal-ca" },
      },
    },
    { provider, dependsOn: [caSecret] }
  );

  return chart;
}
