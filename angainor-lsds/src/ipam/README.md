# LSDSuite IPAM Plugin

This is a IPAM plugin for Docker. It is composed of two parts: the first,
`server`, runs as a service on your Docker Swarm and is responsible for IP
address allocation, the second, `plugin`, is installed as plugin on all nodes
and forwards request to `server`.

## Building

Run `make` to build the plugin and server. Cutomize their names with
`make PLUGIN_NAME=xxx SERVER_NAME=yyy`.

Run `make push` to push them to a registry. See above for name customization.

## Usage

Once built, run `docker plugin enable 127.0.0.1:5000/lsdsuite/ipam:latest` to
activate the plugin. Start the server with:

```bash
docker service create --name lsdsuite-ipam -p 7001:7001
127.0.0.1:5000/lsdsuite/ipam-server
```

Then, a network can be created using `127.0.0.1:5000/lsdsuite/ipam:latest` as IPAM plugin:

```bash
docker network create \
  --ipam-driver=127.0.0.1:5000/lsdsuite/ipam:latest \
  --subnet=172.30.0.0/16 \
  my-network
```

Optionally, the gateway IP can be provided with `--gateway=172.30.255.1`,
otherwise `lsdsuite/ipam` tries to determine it based on the subnet (172.30.0.1
in this example).


## Implementation details

This plugin allocates IP addresses sequentially in the IP range, and records the time when addresses are freed by Docker. Once all IPs in the range have been used, new addresses are allocated in order of their de-allocation time.
