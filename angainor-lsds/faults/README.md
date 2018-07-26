# Faults

The command `cluster up` makes the system deploy all faults present in this folder to all the nodes in the cluster.

__Disclaimer:__ For all faults it is assumed that there is at least an implementation of `sh` like the one in `busybox`. The `alpine` container image already comes with `busybox` installed.

There are two faults implemented:
- Waste CPU
- Kill Containers

## waste_CPU
Run mathmatical operations in order to consume CPU

Has 2 Arguments:
- time: number of seconds
- number_cores: number of cores to exhaust [Default: 1]

------

Additionally, we though of the following faults, which are NOT IMPLEMENTED:

- Resource exhaustion
- Disk Corruption
- Clock Skew

# Resource Exhaustion

## waste_IO
Create a series of Reads and Writes to consume IO operations

Has 3 Arguments:
- time: number of seconds
- r_requests: number of READ requests to the disk per second
- w_requests: number of WRITE requests to the disk per second

## waste_MEM
Allocate RAM to comsume Virtual Memory

Has 2 Arguments:
- time: number of seconds
- mem: Amount in MBs (?) to use

# Disk corruption

## Sector Corruption
Study two options:
1. Corrupt the physical disk (may affect other containers if shared volume)
2. intercept read operations and return corrupted result

## File Corruption
Corrupt the sectors in which a file is located

Study two options:
1. Corrupt the physical disk (may affect other containers if shared volume)
2. intercept read operations and return corrupted result

# Clock skew

This fault affects all the containers running in a node

Has 1 argument:
- amount: The number of seconds to skew (positve or negative value)
