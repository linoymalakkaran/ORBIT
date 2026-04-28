/**
 * k8s/kafka.ts
 * Deploys Strimzi Kafka operator + a 3-broker Kafka cluster.
 * Creates Day-1 topics via KafkaTopic CRs.
 */
import * as k8s from "@pulumi/kubernetes";
import { NAMESPACES, resourceName } from "../shared/platform";

const DAY1_TOPICS: Array<{ name: string; partitions: number; replicas: number; retentionMs: number }> = [
  { name: "portal.ledger.events",    partitions: 6,  replicas: 3, retentionMs: 30 * 24 * 3600 * 1000 },
  { name: "portal.stage.transitions",partitions: 6,  replicas: 3, retentionMs:  7 * 24 * 3600 * 1000 },
  { name: "portal.health.probes",    partitions: 3,  replicas: 3, retentionMs:  3 * 24 * 3600 * 1000 },
  { name: "portal.notifications",    partitions: 3,  replicas: 3, retentionMs:  1 * 24 * 3600 * 1000 },
];

export function deployKafka(
  provider: k8s.Provider,
  env: string,
  namespaceDep: k8s.core.v1.Namespace,
): { operator: k8s.helm.v3.Release; cluster: k8s.apiextensions.CustomResource } {
  const isProd = env === "prod";

  // 1. Strimzi operator
  const operator = new k8s.helm.v3.Release(
    resourceName("strimzi", env),
    {
      name:           "strimzi-kafka-operator",
      chart:          "strimzi-kafka-operator",
      repositoryOpts: { repo: "https://strimzi.io/charts" },
      version:        "0.43.0",
      namespace:      NAMESPACES.data,
      values: {
        image: {
          registry:   "harbor.ai.adports.ae",
          repository: "strimzi/operator",
          tag:        "0.43.0",
        },
        watchAnyNamespace: false,
        resources: {
          requests: { cpu: "200m", memory: "384Mi" },
          limits:   { cpu: "500m", memory: "512Mi" },
        },
      },
      waitForJobs: true,
    },
    { provider, dependsOn: [namespaceDep] }
  );

  // 2. Kafka cluster
  const cluster = new k8s.apiextensions.CustomResource(
    resourceName("kafka-cluster", env),
    {
      apiVersion: "kafka.strimzi.io/v1beta2",
      kind: "Kafka",
      metadata: {
        name: `orbit-kafka-${env}`,
        namespace: NAMESPACES.data,
        labels: { "project": "orbit", env },
      },
      spec: {
        kafka: {
          version: "3.7.1",
          replicas: isProd ? 3 : 1,
          listeners: [
            {
              name: "plain",
              port: 9092,
              type: "internal",
              tls: false,
            },
            {
              name: "tls",
              port: 9093,
              type: "internal",
              tls: true,
              authentication: { type: "tls" },
            },
          ],
          config: {
            "offsets.topic.replication.factor": isProd ? 3 : 1,
            "transaction.state.log.replication.factor": isProd ? 3 : 1,
            "transaction.state.log.min.isr": isProd ? 2 : 1,
            "default.replication.factor": isProd ? 3 : 1,
            "min.insync.replicas": isProd ? 2 : 1,
            "log.message.format.version": "3.7",
            "inter.broker.protocol.version": "3.7",
          },
          storage: {
            type: "persistent-claim",
            size: isProd ? "50Gi" : "10Gi",
            deleteClaim: false,
          },
          resources: {
            requests: { memory: isProd ? "2Gi" : "512Mi", cpu: "500m" },
            limits:   { memory: isProd ? "4Gi" : "1Gi",   cpu: "1" },
          },
          metricsConfig: {
            type: "jmxPrometheusExporter",
            valueFrom: {
              configMapKeyRef: {
                name: "kafka-metrics",
                key:  "kafka-metrics-config.yml",
              },
            },
          },
        },
        zookeeper: {
          replicas: isProd ? 3 : 1,
          storage: {
            type: "persistent-claim",
            size: isProd ? "10Gi" : "5Gi",
            deleteClaim: false,
          },
          resources: {
            requests: { memory: "512Mi", cpu: "250m" },
            limits:   { memory: "1Gi",   cpu: "500m" },
          },
        },
        entityOperator: {
          topicOperator:  { resources: { requests: { cpu: "100m", memory: "128Mi" }, limits: { cpu: "200m", memory: "256Mi" } } },
          userOperator:   { resources: { requests: { cpu: "100m", memory: "128Mi" }, limits: { cpu: "200m", memory: "256Mi" } } },
        },
      },
    },
    { provider, dependsOn: [operator] }
  );

  // 3. Day-1 KafkaTopic CRs
  DAY1_TOPICS.forEach((topic) => {
    new k8s.apiextensions.CustomResource(
      `kafka-topic-${topic.name.replace(/\./g, "-")}-${env}`,
      {
        apiVersion: "kafka.strimzi.io/v1beta2",
        kind: "KafkaTopic",
        metadata: {
          name: topic.name,
          namespace: NAMESPACES.data,
          labels: {
            "strimzi.io/cluster": `orbit-kafka-${env}`,
            "project": "orbit",
            env,
          },
        },
        spec: {
          partitions: topic.partitions,
          replicas:   isProd ? topic.replicas : 1,
          config: {
            "retention.ms":     topic.retentionMs.toString(),
            "cleanup.policy":   "delete",
            "compression.type": "lz4",
          },
        },
      },
      { provider, dependsOn: [cluster] }
    );
  });

  return { operator, cluster };
}
