#!/bin/mksh

set -vex

# maor load
function config_workloads
{
    sed -i "s/recordcount=[0-9]*/recordcount=${RECNUM:=1000000}/g" \
        /opt/ycsb-*/workloads/workload*
    sed -i "s/operationcount=[0-9]*/operationcount=${OPNUM:=5000000}/g" \
        /opt/ycsb-*/workloads/workload*

    return
}

function load_data
{
    if [[ ! -e /.loaded_data ]]; then

        /opt/ycsb-*/bin/ycsb.sh load "${DBTYPE}" -s -p measurementtype=timeseries -p timeseries.granularity=1000 -P "workloads/workload${WORKLETTER}" "${DBARGS}" && touch /.loaded_data
    fi

    return
}

# exit message
trap 'echo "\n$container has finished\n"' EXIT
echo "\ncontainer has started\n"

# make it easier to see logs in the rancher ui
THREADS=${THREADS:-"1"}
echo "Threads: ${THREADS}"

# make sure all the params are set and go.
if [[ -z ${DBTYPE} || -z ${WORKLETTER} || -z ${DBARGS} ]]; then
  echo "Missing params! Exiting"
  exit 1
else
  config_workloads
  if [[ ! -z "${ACTION}" ]]; then
    eval ./bin/ycsb "${ACTION}" "${DBTYPE}" -threads "${THREADS}"  -s -p measurementtype=timeseries -p timeseries.granularity=1000 -P "workloads/workload${WORKLETTER}" "${DBARGS}"
  else
    load_data
    eval ./bin/ycsb run "${DBTYPE}" -threads "${THREADS}" -s -p measurementtype=timeseries -p timeseries.granularity=1000 -P "workloads/workload${WORKLETTER}" "${DBARGS}"
  fi
fi
