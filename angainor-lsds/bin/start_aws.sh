#!/usr/bin/env bash
set -euo pipefail

if [[ $# < 2 ]]
then
    echo "Usage: $0 N_INSTANCE INSTANCE_TYPE [REGION (default: us-east-1)]"
    echo "       Use INSTANCE_TYPE=local to create local VMs"
    exit -1
fi

N=$1
INSTANCE_TYPE=$2
REGION=${3:-"us-east-1"}

if [[ "$INSTANCE_TYPE" == "local" ]]
then
    echo "Starting $N $INSTANCE_TYPE instances..."
    INSTANCE_USER=docker
else
    echo "Starting $N $INSTANCE_TYPE instances in $REGION..."
    INSTANCE_USER=ubuntu
fi

for i in $(seq 0 $((N-1)))
do
    if [[ "$INSTANCE_TYPE" == "local" ]]
    then
        docker-machine create "node-$i"
    else
        docker-machine create --driver amazonec2 \
            --amazonec2-instance-type "$INSTANCE_TYPE" \
            --amazonec2-region "$REGION" \
            "node-$i"
        docker-machine ssh "node-$i" sudo usermod -aG docker ubuntu
    fi
done

echo
echo "Instances started!"

docker-machine ssh "node-0" mkdir -p lsdsuite/keys
docker-machine scp -r "bin" "node-0:lsdsuite/"

echo
echo "Copying SSH keys to manager node"
for i in $(seq 0 $((N-1)))
do
    docker-machine scp ~/.docker/machine/machines/"node-$i"/id_rsa "node-0:lsdsuite/keys/id_rsa.$i"
done

echo
echo "Creating config.yaml..."
CONFIG_FILE=$(mktemp --suffix=.yaml config.XXXXXXXX)
trap "rm $CONFIG_FILE" EXIT

echo "nodes:" > $CONFIG_FILE
for i in $(seq 0 $((N-1)))
do
    # TODO: find a better way for detecting IP. Unfortunately, interface name is different depending on instance type
    IP=$(docker-machine ssh "node-$i"  "ip -4 -o addr show | tail -n+2 | grep -v 'docker' | tail -n1 | grep -Eo 'inet ([0-9]*\.){3}[0-9]*' | cut -c6-")
    echo "  - address: $IP" >> "$CONFIG_FILE"
    echo "    private_key: keys/id_rsa.$i" >> "$CONFIG_FILE"
    echo "    username: $INSTANCE_USER" >> "$CONFIG_FILE"
done

docker-machine scp "$CONFIG_FILE" "node-0:lsdsuite/config.yaml"

echo
echo "config.yaml created:"
cat "$CONFIG_FILE"

echo
echo "Starting cluster..."
eval $(docker-machine env --shell=bash node-0)
make
docker-machine ssh node-0 -t 'cd lsdsuite; bin/lsds cluster init && bin/lsds cluster registry'
make push
docker-machine ssh node-0 -t 'cd lsdsuite; bin/lsds -v cluster up'

echo
echo "DONE !"
echo
