/**
 * k8s/namespaces.ts
 * Creates all ORBIT namespaces with Pod Security Standards enforcement.
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES } from "../shared/platform";

export function createNamespaces(
  provider: k8s.Provider,
  env: string,
): k8s.core.v1.Namespace[] {
  const namespaceSpecs: Array<{ name: string; pss: string }> = [
    { name: NAMESPACES.system,        pss: "restricted" },
    { name: NAMESPACES.core,          pss: "restricted" },
    { name: NAMESPACES.data,          pss: "restricted" },
    { name: NAMESPACES.agents,        pss: "restricted" },
    { name: NAMESPACES.vault,         pss: "restricted" },
    { name: NAMESPACES.keycloak,      pss: "restricted" },
    { name: NAMESPACES.observability, pss: "restricted" },
  ];

  return namespaceSpecs.map(
    ({ name, pss }) =>
      new k8s.core.v1.Namespace(
        name,
        {
          metadata: {
            name,
            labels: {
              "app.kubernetes.io/managed-by": "pulumi",
              "project": "orbit",
              "env": env,
              // Pod Security Standards
              "pod-security.kubernetes.io/enforce": pss,
              "pod-security.kubernetes.io/audit":   pss,
              "pod-security.kubernetes.io/warn":    pss,
            },
          },
        },
        { provider, protect: env === "prod" }
      )
  );
}
