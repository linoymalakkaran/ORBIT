/**
 * k8s/metallb.ts
 * Deploys MetalLB in L2 mode via Helm, then configures an IPAddressPool.
 * Required before any LoadBalancer Service can get an external IP on-prem.
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

export function deployMetalLb(
  provider: k8s.Provider,
  env: string,
  ipRange: string,
  namespaceDep: k8s.core.v1.Namespace,
): k8s.helm.v3.Release {
  const chart = new k8s.helm.v3.Release(
    resourceName("metallb", env),
    {
      name:            "metallb",
      chart:           "metallb",
      repositoryOpts:  { repo: "https://metallb.github.io/metallb" },
      version:         "0.14.8",
      namespace:       NAMESPACES.system,
      values: {
        controller: {
          resources: {
            requests: { cpu: "100m", memory: "100Mi" },
            limits:   { cpu: "200m", memory: "200Mi" },
          },
        },
        speaker: {
          resources: {
            requests: { cpu: "100m", memory: "100Mi" },
            limits:   { cpu: "200m", memory: "200Mi" },
          },
        },
      },
      waitForJobs: true,
    },
    { provider, dependsOn: [namespaceDep] }
  );

  // IPAddressPool CR — allocate the on-prem IP range to LoadBalancer services
  const ipPool = new k8s.apiextensions.CustomResource(
    resourceName("metallb-ippool", env),
    {
      apiVersion: "metallb.io/v1beta1",
      kind: "IPAddressPool",
      metadata: {
        name: "orbit-pool",
        namespace: NAMESPACES.system,
        labels: { "project": "orbit", env },
      },
      spec: {
        addresses: [ipRange],
      },
    },
    { provider, dependsOn: [chart] }
  );

  // L2Advertisement — tell MetalLB to announce via ARP
  new k8s.apiextensions.CustomResource(
    resourceName("metallb-l2advert", env),
    {
      apiVersion: "metallb.io/v1beta1",
      kind: "L2Advertisement",
      metadata: {
        name: "orbit-l2",
        namespace: NAMESPACES.system,
        labels: { "project": "orbit", env },
      },
      spec: {
        ipAddressPools: ["orbit-pool"],
      },
    },
    { provider, dependsOn: [ipPool] }
  );

  return chart;
}
