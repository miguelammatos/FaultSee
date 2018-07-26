#!/bin/mksh

set -e

# maor load
function config_workloads
{
    sed -i "s/recordcount=[0-9]*/recordcount=${RECNUM:=1000000}/g" \
        /source-code/config/workloads/workload*
    sed -i "s/operationcount=[0-9]*/operationcount=${OPNUM:=5000000}/g" \
        /source-code/config/workloads/workload*
    return
}
# avoid repeating client ids
function config_client_init_id
{
    # make sure it is set
    START_CLIEND_ID=${START_CLIEND_ID:=1}
    # make it multiples of 10000
    START_CLIEND_ID=$((START_CLIEND_ID * 10000))
    sed -i "s/smart\-initkey=[0-9]*/smart\-initkey=${START_CLIEND_ID}/g" \
        /source-code/config/workloads/workload*
    return
}

# exit message
trap 'echo "\n$container has finished\n"' EXIT
echo "\ncontainer has started\n"

THREADS=${THREADS:-"1"}
echo "Threads: ${THREADS}"

# make sure all the params are set and go.
config_workloads
config_client_init_id

if [[ -z "${ACTION}" ]]; then
  echo "Action Env needs to be set"
else
  if [ "${ACTION}" == "load" ]; then
    java -Dlogback.configurationFile="./config/logback.xml" -cp ./lib/*:./bin/ com.yahoo.ycsb.Client -load -threads "${THREADS}" -P config/workloads/workloada -s -p measurementtype=timeseries -p timeseries.granularity=1000 -db bftsmart.demo.ycsb.YCSBClient -p hosts=tasks.server
  elif [ "${ACTION}" == "run" ]; then
    java -Dlogback.configurationFile="./config/logback.xml" -cp ./lib/*:./bin/ com.yahoo.ycsb.Client -t    -threads "${THREADS}" -P config/workloads/workloada -s -p measurementtype=timeseries -p timeseries.granularity=1000 -db bftsmart.demo.ycsb.YCSBClient -p hosts=tasks.server
  else
    "Action Env can either be load or run"
    return 1
  fi
fi
