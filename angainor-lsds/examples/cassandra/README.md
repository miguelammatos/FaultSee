There are 6 Workloads in YCSB, in the experiment we will focus on the first 2.

```
Workload A: Update heavy workload: 50/50% Mix of Reads/Writes
Workload B: Read mostly workload: 95/5% Mix of Reads/Writes
Workload C: Read-only: 100% reads
Workload D: Read the latest workload: More traffic on recent inserts
Workload E: Short ranges: Short range based queries
Workload F: Read-modify-write: Read, modify and update existing records
```
There are 3 experiments:
- Clean - No intervention
- CPU - Exhaust CPU
- KILL NODE - kills a cassandra node

The simple variant runs a quicker experiment



## <a name="references-ports"></a>Ports

These are the ports exposed by the container image.

| **Port** | **Description** |
|:---------|:----------------|
| TCP 7000 | Cassandra inter-node cluster communication. |
| TCP 7001 | Cassandra SSL inter-node cluster communication. |
| TCP 7199 | Cassandra JMX monitoring port. |
| TCP 9042 | Cassandra client port. |
| TCP 9160 | Cassandra Thrift client port. |
| TCP 9404 | Prometheus plugin port. |
