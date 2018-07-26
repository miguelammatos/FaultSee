# LSDSuite Node Manager

## Building and pushing to a repo

In the makefile, change the `$$USER` variable to your username in Docker Hub Repo

```bash
make all
```

## Running the lsdsuite-slave service

The following options must be specified:

- Mount points (host -> container):
    - /var/run/docker.sock -> /var/run/docker.sock (to access Docker daemon)
    - $LSDSUITE_DIR/sock   -> /app/sock  (socket for log driver will be here)
    - $LSDSUITE_DIR/logs   -> /app/logs  (log files are saved here)
    - /proc                -> /app/proc  (for resource usage stats)
    - /sys                 -> /app/sys   (same)
- `--network=host` (for network stats)
- Env variables:
    - `HOST_PROC=/app/proc`
    - `HOST_SYS=/app/sys`
- Publish port 7000

The `$LSDSUITE_DIR/{sock,logs}` directories must already exist on all nodes:
```bash
mkdir -p $LSDSUITE_DIR/{sock,logs}
```

```bash
docker service create --name lsdsuite-slave \
  --detach=false \
  --mode=global \
  --network=host \
  --publish mode=host,target=7000,published=7000 \
  --mount type=bind,source=/var/run/docker.sock,destination=/var/run/docker.sock \
  --mount type=bind,source=$LSDSUITE_DIR/sock,destination=/app/sock \
  --mount type=bind,source=$LSDSUITE_DIR/logs,destination=/app/logs \
  --mount type=bind,source=/proc,destination=/app/proc,ro=true \
  --mount type=bind,source=/sys,destination=/app/sys,ro=true \
  --env HOST_PROC=/app/proc --env HOST_SYS=/app/sys \
  $$USER/faultsee-slave
```

## Running containers on lsdsuite-slave

To connect a container or service's log output to lsdsuite-slave, the following options must be specified:

- `log-driver`: `syslog`
- `log-opt`: `syslog-address=unix://$LSDSUITE_DIR/sock/logs.sock`
- `log-opt`: `syslog-format=rfc5424micro`
- `log-opt`:  `tag='{{.FullID}}'`

Additionally, if the containers' stats need to be logged, add the label `org.lsdsuite.stats=true`.

### Single container
```bash
docker run \
  --log-driver syslog \
  --log-opt syslog-address=unix://$LSDSUITE_DIR/sock/logs.sock \
  --log-opt syslog-format=rfc5424micro \
  --log-opt tag='{{.FullID}}' \
  --label org.lsdsuite.stats=true \
  $IMAGE
```
### Services
```bash
docker service create --name=$SERVICE_NAME \
  --detach=false \
  --log-driver syslog \
  --log-opt syslog-address=unix://$LSDSUITE_SLAVE/sock/logs.sock \
  --log-opt syslog-format=rfc5424micro \
  --log-opt tag='{{.FullID}}' \
  --container-label org.lsdsuite.stats=true \
  $IMAGE
```

## Commands

Each lsdsuite-slave instance accepts JSON commands sent through TCP in the form
`{"command": "[COMMAND]", "params": {...}}` (`params` being optional),
and responds with a JSON object like `{"status": "ok|err" [, "msg": "..."]}`.

Examples:
```bash
echo '{"command": "status"}' | ncat localhost 7000
# => '{"status":"ok","msg":"[HOSTNAME]"}'
echo '{"command": "kill", "params": {"id": "abcd0123"}}' | ncat localhost 7000
# => '{"status":"ok"}'
```

These commands are implemented:

- `status`: reply with hostname.
- `log`, `params: {file: [LOG_FILE]}`: switch logging output to `LOG_FILE`, or `default.log` if not supplied.
- `kill`, `params: {id: [CONTAINER_ID], signal: [SIGNAL]}`: kill container `CONTAINER_ID` with signal `SIGNAL` (or `SIGTERM` if not supplied).
- `pause`/`unpause`, `params`: `{id: [CONTAINER_ID]}`: pause/unpause container `CONTAINER_ID`.
- `pull`, `params`: `{image: [IMAGE]}`: pull image `IMAGE`.
- `mark`, `params`: `{msg: [MSG]}`: insert log entry `MSG` in log stream.
