# FaultSee Framework

## Quickstart

### Preparations

Once all dependencies have been installed (see *Dependencies* below), prepare your nodes by installing Docker and make sure they are SSH-accessible.

### Configuration

Create a file `config.yaml` (see `examples/config.yaml`) containing your
cluster's configuration. The most important option is **nodes**. It is a list of
all nodes of the cluster. For each node, the IP address must be specified, as
well a SSH credentials to access it (username and password or private key). The
exception to this is the first node, which is considered to be the node where
lsdsuite is running and will be set up as Docker Swarm manager. Only the address
of the first node must be specified.

```yaml
nodes:
  - address: 192.168.99.1
  - address: 192.168.99.100
    private_key: /path/to/id_rsa
    username: docker
  - address: 192.168.99.101
    password: pa$$w0rd
    username: john
```

The other options in this file have sensible default values and don't need to be
changed. These options are:

**lsdsuite_dir**:

Directory where the mount points for the lsdsuite-slave service are located. The
subdirectories `logs` and `sock` will automatically be created. Default value is
`/tmp/lsdsuite`. Since logs are automatically retrieved to `results_dir`, this
directory doesn't need to be persistent.


**results_dir**:

Logs will be copied to this directory after each benchmark run. Default value is `./results`.


**slave_image**:

Reference to the lsdsuite-slave image. Default value is
`mapa12/faultsee-slave:dev_latest`, corresponding to the build instructions for
lsdsuite-slave.


**slave_port**:

Port on which the lsdsuite-service is reachable. Default value is `7000`.


**docker_sock**:

Path to the docker socket. Default value is `/var/run/docker.sock`.

### Cluster initialization

Run `bin/lsds cluster init`, followed by `bin/lsds cluster registry` to start a
private Docker registry. Once this is done, follow build and push the
lsdsuite-image:

```bash
docker build -t 127.0.0.1:5000/lsdsuite/slave ../lsdsuite-slave
docker push 127.0.0.1:5000/lsdsuite/slave
```

You can now run `bin/lsds cluster up` to set the whole cluster up. Run `bin/lsds
cluster status` to check its status.

### Benchmarks

A benchmark is described by two files. The first describes the application,
which services to run and how the network is configured (see `examples/app.yaml`
and `examples/sock-test.yaml`). The second specifies churn applied during the
benchmark (see `examples/churn.yaml`). This file is optional: if a benchmark is
run without churn specification, its duration must be specified instead with the
`--run-time` command-line option.

To start a benchmark, run:
```bash
bin/lsds benchmark --app [APP_FILE] --name [BENCHMARK_NAME] --churn [CHRUN_FILE]
```

To run the same benchmark multiple times in succession, specify the number of runs with `--runs`

For more details, run `bin/lsds benchmark --help`

### Logs

After each benchmark, the logs of each node are copied to a subfolder of `results_dir`, named `[DATE+TIME]--[BENCHMARK_NAME]/run-[N]`. Here, each individual node's logs are saved under `nodes/`. All logs are additionally concatenated and sorted by time in `out.log`.

Each log line contains the following fields:

- Date and time of log entry, in ISO 8601 format with microsecond precision
- Topic of the log entry, explained below
- Author of the entry, either node hostname or container ID
- Log message

All fields are tab-separated, except date and topic which are separated by a space.

Possible log topics are:

- `[LOG]`: message is a line of container's stdout, author is container's ID
- `[STATS]`: a container's resource usage stats, in JSON format
- `[HOST]`: a node's resource usage stats, in JSON format
- `[EVENT]`: Docker events, such as container creation/killing/...
- `[MARK]`: markers on some events, such as benchmark start/end and churn steps.

Collecting container usage stats can impact performance. Because of this, it is disabled by default. To enable it for specific services, add the following to the service specifications:

```yaml
labels:
  org.lsdsuite.stats: "true"
```

## Dependencies

lsdsuite-master requires the following Python dependencies:

- docker
- pyyaml
- paramiko
- click

For container orchestration, Docker is used. All nodes must have Docker version 17.09 installed, and be accessible through SSH. The user through which nodes are accessed must be part of the docker group.
