/**
 * k8s/argocd.ts
 * Deploys ArgoCD, creates the orbit AppProject, and bootstraps
 * the app-of-apps Application. After this runs, ArgoCD takes over
 * deploying all other services from the Git repo.
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

const GIT_REPO   = "https://github.com/linoymalakkaran/ORBIT.git";
const GIT_BRANCH = "main";

export function deployArgoCD(
  provider: k8s.Provider,
  env: string,
  namespaceDep: k8s.core.v1.Namespace,
  vaultDep: k8s.helm.v3.Release,
): k8s.helm.v3.Release {
  const isProd = env === "prod";

  const chart = new k8s.helm.v3.Release(
    resourceName("argocd", env),
    {
      name:           "argocd",
      chart:          "argo-cd",
      repositoryOpts: { repo: "https://argoproj.github.io/argo-helm" },
      version:        "7.6.12",
      namespace:      NAMESPACES.system,
      values: {
        global: {
          image: {
            repository: "harbor.ai.adports.ae/argoproj/argocd",
            tag:        "v2.12.6",
          },
        },
        server: {
          replicas: isProd ? 2 : 1,
          resources: {
            requests: { cpu: "100m", memory: "256Mi" },
            limits:   { cpu: "500m", memory: "512Mi" },
          },
          config: {
            "admin.enabled": "true",
            "application.resourceTrackingMethod": "annotation",
            "timeout.reconciliation": "180s",
          },
        },
        controller: {
          replicas: isProd ? 2 : 1,
          resources: {
            requests: { cpu: "250m", memory: "512Mi" },
            limits:   { cpu: "1",    memory: "1Gi" },
          },
        },
        repoServer: {
          replicas: isProd ? 2 : 1,
          resources: {
            requests: { cpu: "100m", memory: "256Mi" },
            limits:   { cpu: "500m", memory: "512Mi" },
          },
        },
        applicationSet: {
          replicas: isProd ? 2 : 1,
        },
        configs: {
          repositories: {
            "orbit-repo": {
              url:  GIT_REPO,
              name: "orbit",
              type: "git",
            },
          },
        },
      },
    },
    { provider, dependsOn: [namespaceDep, vaultDep] }
  );

  // AppProject — scopes all ORBIT applications
  const project = new k8s.apiextensions.CustomResource(
    resourceName("argocd-project", env),
    {
      apiVersion: "argoproj.io/v1alpha1",
      kind: "AppProject",
      metadata: {
        name:      "orbit",
        namespace: NAMESPACES.system,
        labels:    { "project": "orbit", env },
      },
      spec: {
        description: "ORBIT AI Portal — all infrastructure and application workloads",
        sourceRepos: [GIT_REPO],
        destinations: [
          { server: "https://kubernetes.default.svc", namespace: "*" },
        ],
        clusterResourceWhitelist: [
          { group: "*", kind: "*" },
        ],
        namespaceResourceWhitelist: [
          { group: "*", kind: "*" },
        ],
      },
    },
    { provider, dependsOn: [chart] }
  );

  // App-of-apps — ArgoCD manages itself after this bootstrap
  new k8s.apiextensions.CustomResource(
    resourceName("argocd-app-of-apps", env),
    {
      apiVersion: "argoproj.io/v1alpha1",
      kind: "Application",
      metadata: {
        name:      "orbit-infra",
        namespace: NAMESPACES.system,
        labels:    { "project": "orbit", env },
        finalizers: ["resources-finalizer.argocd.argoproj.io"],
      },
      spec: {
        project: "orbit",
        source: {
          repoURL:        GIT_REPO,
          targetRevision: GIT_BRANCH,
          path:           `src/infrastructure/argocd/apps/${env}`,
        },
        destination: {
          server:    "https://kubernetes.default.svc",
          namespace: NAMESPACES.system,
        },
        syncPolicy: {
          automated: {
            prune:    true,
            selfHeal: true,
          },
          syncOptions: ["CreateNamespace=true"],
        },
      },
    },
    { provider, dependsOn: [project] }
  );

  return chart;
}
