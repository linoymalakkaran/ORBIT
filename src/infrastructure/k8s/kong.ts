/**
 * k8s/kong.ts
 * Deploys Kong Ingress Controller (KIC) for all external traffic routing.
 * Services are exposed via KongIngress + Ingress objects in their own namespaces.
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

export function deployKong(
  provider: k8s.Provider,
  env: string,
  domain: string,
  namespaceDep: k8s.core.v1.Namespace,
  metallbDep: k8s.helm.v3.Release,
  certManagerDep: k8s.helm.v3.Release,
): k8s.helm.v3.Release {
  return new k8s.helm.v3.Release(
    resourceName("kong", env),
    {
      name:           "kong",
      chart:          "kong",
      repositoryOpts: { repo: "https://charts.konghq.com" },
      version:        "2.43.0",
      namespace:      NAMESPACES.system,
      values: {
        image: {
          repository: `harbor.ai.adports.ae/kong/kong`,
          tag:        "3.8.0",
        },
        ingressController: {
          enabled: true,
          image: {
            repository: "harbor.ai.adports.ae/kong/kubernetes-ingress-controller",
            tag:        "3.3.1",
          },
          resources: {
            requests: { cpu: "100m", memory: "256Mi" },
            limits:   { cpu: "500m", memory: "512Mi" },
          },
        },
        proxy: {
          type: "LoadBalancer",
          loadBalancerIP: "",   // MetalLB will assign from pool
          tls: { enabled: true },
          http: { enabled: true },
          resources: {
            requests: { cpu: "200m", memory: "256Mi" },
            limits:   { cpu: "1",    memory: "512Mi" },
          },
        },
        env: {
          database:   "off",
          router_flavor: "expressions",
          proxy_listen:   "0.0.0.0:8000, 0.0.0.0:8443 ssl",
          ssl_cert:       "/etc/secrets/orbit-wildcard-tls/tls.crt",
          ssl_cert_key:   "/etc/secrets/orbit-wildcard-tls/tls.key",
          log_level:      "notice",
        },
        secretVolumes: ["orbit-wildcard-tls"],
        podSecurityContext: {
          runAsUser: 1000,
          runAsNonRoot: true,
        },
        containerSecurityContext: {
          allowPrivilegeEscalation: false,
        },
        metrics: {
          enabled: true,
          serviceMonitor: { enabled: true },
        },
      },
    },
    { provider, dependsOn: [namespaceDep, metallbDep, certManagerDep] }
  );
}
