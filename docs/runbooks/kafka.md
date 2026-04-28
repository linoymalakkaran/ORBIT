# Kafka (Strimzi) Runbook

## Overview
ORBIT uses **Strimzi** operator to manage a Kafka 3.7.1 cluster in namespace `ai-portal-data`.  
Dev: 1 broker | Prod: 3 brokers + 3 Zookeeper (or KRaft mode).

---

## Topics

| Topic | Retention | Purpose |
|-------|-----------|---------|
| `portal.ledger.events` | 30 days | Immutable audit log |
| `portal.stage.transitions` | 7 days | Pipeline state changes |
| `portal.health.probes` | 3 days | Health check events |
| `portal.notifications` | 1 day | User notifications |

---

## Common Operations

### Check Kafka cluster status
```bash
kubectl -n ai-portal-data get kafka orbit-kafka
kubectl -n ai-portal-data describe kafka orbit-kafka
```

### List topics
```bash
kubectl -n ai-portal-data exec -it orbit-kafka-kafka-0 \
  -c kafka -- bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list
```

### Describe a topic
```bash
kubectl -n ai-portal-data exec -it orbit-kafka-kafka-0 \
  -c kafka -- bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic portal.ledger.events
```

### Produce test message
```bash
kubectl -n ai-portal-data exec -it orbit-kafka-kafka-0 \
  -c kafka -- bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 \
  --topic portal.ledger.events
```

### Consume from beginning
```bash
kubectl -n ai-portal-data exec -it orbit-kafka-kafka-0 \
  -c kafka -- bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic portal.ledger.events \
  --from-beginning --max-messages 10
```

### Check consumer group lag
```bash
kubectl -n ai-portal-data exec -it orbit-kafka-kafka-0 \
  -c kafka -- bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --describe --all-groups
```

---

## Adding a New Topic

Create a `KafkaTopic` CR:
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: portal.my-new-topic
  namespace: ai-portal-data
  labels:
    strimzi.io/cluster: orbit-kafka
spec:
  partitions: 6
  replicas: 1
  config:
    retention.ms: "86400000"   # 1 day
    cleanup.policy: delete
```

---

## Alerts

| Alert | Meaning | Action |
|-------|---------|--------|
| `KafkaBrokerDown` | Pod not ready | Check logs: `kubectl logs orbit-kafka-kafka-0 -c kafka` |
| `KafkaUnderReplicatedPartitions` | Partitions not fully replicated | Check broker count matches topic replicas |
| `KafkaConsumerGroupLag` | Lag > threshold | Scale consumer deployment |
