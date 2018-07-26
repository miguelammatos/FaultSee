# registry

Module that supports lsdsuite by creating a docker-registry with HTTPS (letsencrypt)

Configure required DNS name for registry in `registry/docker-compose.yml`

There are two different services:

- Registry
- UI-Registry

The latter exposes a web interface to browse images in the registry

# Setup

Create the docker network for nginx to proxy requests

`docker network create nginx-proxy`

Launch nginx-proxy and letsencrypt (-d is to run in the background)

`(cd nginx-proxy ; docker-compose up -d)`

Launch the registry and registry-ui

`(cd registry ; docker-compose up -d)`

Access both the registry and the registry-ui through the web browser to confirm both are being served through HTTPS (Try at least 5 times with 3 seconds interval for each)
