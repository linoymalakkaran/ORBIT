/**
 * stacks/tanzu/index.ts
 *
 * Provisions a TKG 2.x workload cluster on vSphere 8 via @pulumi/vsphere.
 *
 * WHAT THIS STACK DOES:
 *   1. Creates a vSphere resource pool and VM folder for the cluster nodes.
 *   2. Deploys a TKG workload cluster using the TanzuKubernetesCluster API
 *      (v1alpha3 supervisor CRD) via a Kubernetes manifest applied to the
 *      TKG supervisor / management cluster.
 *   3. Waits for the cluster kubeconfig to become available.
 *   4. Exports kubeconfig + cluster endpoint (consumed by k8s/ stack via
 *      StackReference).
 *
 * HOW TO USE:
 *   pulumi stack select dev        # or prod
 *   pulumi config set vsphere:vsphereUser "svc-orbit@vsphere.local" --secret
 *   pulumi config set vsphere:vspherePassword "<password>" --secret
 *   pulumi config set orbit-tanzu-cluster:internalCaCert "<base64-pem>" --secret
 *   pulumi up
 *
 * PREREQUISITES:
 *   - TKG management cluster is running and healthy.
 *   - `tanzu login` completed and management cluster context set.
 *   - kubectl context pointed at the management cluster (mgmtContext config).
 *   - vSphere account has permissions on the resource pool + folder.
 */

import * as pulumi from "@pulumi/pulumi";
import * as vsphere from "@pulumi/vsphere";
import * as k8s from "@pulumi/kubernetes";
import { commonTags, resourceName } from "../../shared/platform";

const cfg = new pulumi.Config();
const projectCfg = new pulumi.Config("orbit-tanzu-cluster");

const env             = projectCfg.require("env");
const datacenter      = projectCfg.require("datacenter");
const vsphereCluster  = projectCfg.require("vsphereCluster");
const datastore       = projectCfg.require("datastore");
const network         = projectCfg.require("network");
const resourcePoolId  = projectCfg.require("resourcePool");
const vmFolder        = projectCfg.require("vmFolder");
const mgmtContext     = projectCfg.require("mgmtContext");
const metallbIpRange  = projectCfg.require("metallbIpRange");

const cpCount         = parseInt(projectCfg.require("controlPlaneCount"));
const cpCpu           = parseInt(projectCfg.require("controlPlaneCpu"));
const cpMemMb         = parseInt(projectCfg.require("controlPlaneMemoryMb"));
const sysCount        = parseInt(projectCfg.require("workerSystemCount"));
const sysCpu          = parseInt(projectCfg.require("workerSystemCpu"));
const sysMemMb        = parseInt(projectCfg.require("workerSystemMemoryMb"));
const appCount        = parseInt(projectCfg.require("workerAppCount"));
const appCpu          = parseInt(projectCfg.require("workerAppCpu"));
const appMemMb        = parseInt(projectCfg.require("workerAppMemoryMb"));

const clusterName = resourceName(`tkg-${env}`, env);
const tags = commonTags(env, "01");

// ---------------------------------------------------------------------------
// 1. Lookup vSphere datacenter
// ---------------------------------------------------------------------------
const dc = vsphere.getDatacenter({ name: datacenter });

// ---------------------------------------------------------------------------
// 2. Create a dedicated resource pool for ORBIT nodes
// ---------------------------------------------------------------------------
const parentRp = vsphere.getResourcePool({
  name: resourcePoolId,
  datacenterId: dc.then(d => d.id),
});

const orbitRp = new vsphere.ResourcePool(resourceName("rp", env), {
  name: `orbit-${env}`,
  parentResourcePoolId: parentRp.then(rp => rp.id),
  tags: Object.entries(tags).map(([k, v]) => `${k}=${v}`),
}, { protect: env === "prod" });

// ---------------------------------------------------------------------------
// 3. Create a VM folder to keep nodes tidy
// ---------------------------------------------------------------------------
const orbitFolder = new vsphere.Folder(resourceName("folder", env), {
  path: vmFolder,
  type: "vm",
  datacenterId: dc.then(d => d.id),
});

// ---------------------------------------------------------------------------
// 4. Deploy TanzuKubernetesCluster (TKC) manifest to the management cluster.
//    The TKG supervisor controller reconciles this into actual VMs.
// ---------------------------------------------------------------------------
const mgmtProvider = new k8s.Provider("mgmt-k8s", {
  context: mgmtContext,
});

const tkgCluster = new k8s.apiextensions.CustomResource(
  clusterName,
  {
    apiVersion: "run.tanzu.vmware.com/v1alpha3",
    kind: "TanzuKubernetesCluster",
    metadata: {
      name: clusterName,
      namespace: "default",
      labels: tags,
    },
    spec: {
      topology: {
        controlPlane: {
          replicas: cpCount,
          vmClass: `best-effort-${cpCpu}cpu-${cpMemMb / 1024}gb`,
          storageClass: datastore,
          tkr: {
            reference: {
              // Pin TKR version — update when upgrading K8s
              name: "v1.28.8---vmware.1-tkg.1",
            },
          },
        },
        nodePools: [
          {
            name: "system",
            replicas: sysCount,
            vmClass: `best-effort-${sysCpu}cpu-${sysMemMb / 1024}gb`,
            storageClass: datastore,
            labels: { "node-role": "system" },
            taints: [{ key: "CriticalAddonsOnly", effect: "NoSchedule" }],
          },
          {
            name: "app",
            replicas: appCount,
            vmClass: `best-effort-${appCpu}cpu-${appMemMb / 1024}gb`,
            storageClass: datastore,
            labels: { "node-role": "app" },
          },
          ...(env === "prod"
            ? [{
                name: "batch",
                replicas: parseInt(projectCfg.get("workerBatchCount") ?? "2"),
                vmClass: `best-effort-${projectCfg.get("workerBatchCpu") ?? "8"}cpu-${
                  parseInt(projectCfg.get("workerBatchMemoryMb") ?? "32768") / 1024
                }gb`,
                storageClass: datastore,
                labels: { "node-role": "batch" },
                taints: [{ key: "batch", value: "true", effect: "NoSchedule" }],
              }]
            : []),
        ],
      },
      settings: {
        network: {
          cni: { name: "antrea" },
          pods:     { cidrBlocks: ["192.168.0.0/16"] },
          services: { cidrBlocks: ["10.96.0.0/12"] },
        },
        storage: { defaultClass: datastore },
      },
    },
  },
  { provider: mgmtProvider }
);

// ---------------------------------------------------------------------------
// 5. Export outputs consumed by the k8s/ stack via StackReference
//    NOTE: kubeconfig is marked as a secret — never printed in plain text.
// ---------------------------------------------------------------------------
export const tanzuClusterName = tkgCluster.metadata.name;
export const tanzuClusterNamespace = tkgCluster.metadata.namespace;

// The kubeconfig is retrieved out-of-band via:
//   tanzu cluster kubeconfig get <clusterName> --admin --export-file kubeconfig.yaml
// and stored in Vault at: secret/orbit/kubeconfig/<env>
// The k8s/ stack references it from Vault, not directly from this stack output.
export const metallbIpRangeOut = metallbIpRange;
export const notes = pulumi.output([
  `Cluster '${clusterName}' manifested to management cluster '${mgmtContext}'.`,
  `Wait for: tanzu cluster list --include-management-cluster | grep ${clusterName}`,
  `Then export kubeconfig: tanzu cluster kubeconfig get ${clusterName} --admin --export-file kubeconfig.yaml`,
  `Store it in Vault: vault kv put secret/orbit/kubeconfig/${env} kubeconfig=@kubeconfig.yaml`,
].join("\n"));
