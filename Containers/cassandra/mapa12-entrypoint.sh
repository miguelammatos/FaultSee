#!/bin/sh

echo "Using DNS Name ${DNS_CASSANDRA_NAME}"
getent hosts ${DNS_CASSANDRA_NAME}

export CASSANDRA_SEEDS=$(nrOfTasks=`getent hosts ${DNS_CASSANDRA_NAME} | wc -l` ; many=`getent hosts ${DNS_CASSANDRA_NAME} | awk '{print $1}' | sed "/$(hostname --ip-address)/d" | paste -d, -s -` ; printf '%s' $( [ ${nrOfTasks} -gt 1 ] && echo ${many} || echo "$(hostname --ip-address)" ))
echo "SEEDS: ${CASSANDRA_SEEDS}"
#
# _term() {
#   echo "Caught SIGTERM signal!"
#   echo "Relaying SIGTERM to child"
#   kill -TERM "$child" 2>/dev/null
# }
#
# trap _term TERM
# trap _term INT

/bin/sh -c "/docker-entrypoint.sh cassandra -f"
#
# child=$!
# echo "child is $child"
# ps aux
# wait "$child"
