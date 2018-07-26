#!/usr/bin/env bash
set -ex

# default arguments
export USER=${USER:-"mapa12"}
export REPO=${REPO:-"server-signal-handler"}


docker run -it --rm -p 3000:3000 --name="signal-bg-app" ${USER}/${REPO}
