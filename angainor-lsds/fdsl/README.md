<a name="document-start"></a>
# FDSL

This document describes the Faultsee DSL, referred as FDSL from this point onwards. [TL ; DR](#tldr-anchor) at the end.

The FDSL is used to describe an experiment’s events, it is done by creating a configuration file that complies with YAML syntax.

This configuration file is complementary to the docker-compose compatible file that describes the services that the experiment will be running.

The configuration file contains two main sections, environment and events. Environment defines some options that are specific to each experiment and Events describe the experiment.

Specification:
```yaml
environent:
    seed: seed_value
    ntp_server: URL
events:
    - event_1
    - event_2
    - ...
    - event_N
```

- `seed_value` is an integer that is used to populate the pseudo-random number generator, this way it is possible to replay experiments. By default this number is 789.
- `ntp_server_URL` is a string with the URL of the ntp server to use in order to synchronize the clocks, if not provided the clocks will not be synchronized at the beginning of each experiment round.

There are the following types of events:
- [beginning](#beginning-anchor)
- [end](#end-anchor)
- [moment](#moment-anchor)

# Events Types

<a name="beginning-anchor"></a>
## Beginning

The `beginning` event describes the initial state of the experiment. For each service of the experiment, it defines the number of initial containers.  
This is a mandatory Event and without it the experiment will fail to start. However there can only be one of this event.



Specification:
```yaml
- beginning:
    service_name_1: number_of_containers_on_start_for_service_1
    service_name_2: number_of_containers_on_start_for_service_2
    ...
    service_name_N: number_of_containers_on_start_for_service_N
```

The first line indicates that is an event of type `beginning`.

Then there is a line for each service in the experiment describing the number of containers:

- `service_name_N` is a string
- `number_of_containers_on_start_for_service_N` is an int

All containers will be deployed simultaneously, as such the lines order is irrelevant. If the deploy order is considered important for the experiment, the user can specify service_events of type `start`, explained further ahead in this document.

__Example:__
```yaml
- beginning:
    load-balancer: 1
    web-server: 2
    database: 3
```

<!--
**Is service order important? This is important in many scenarios, i.e. the first service should be started only after the second one. This should be enabled by default with an additional service stating that services can be started in parallel.**
-->
<!--
_The initial values can be zero and the user can create ADD events that will control the order of deployed containers, can we consider this enough?_
-->
The previous example states that when the experiment starts there will be 4 containers running:

- 1 container of the service load-balancer
- 2 containers of the service web-server
- 3 containers of the service database

<a name="end-anchor"></a>
## End
This event indicates when the experiment ends.
This is the other Event that is mandatory and there can only be one as well. Without it the experiment will also fail to start.


Specification:

```yaml
- end: number_of_seconds
```

This event is described in a single line, that describes the second at which the experiment will end.

- `number_of_seconds` is an int.

__Example:__

```yaml
- end: 1000
```

The previous example states that the experiment will end after 1000 seconds have elapsed, since the beginning event.

<a name="moment-anchor"></a>
## Moment

There can be an arbitrary number of Moment events, and they describe the interesting parts of an experiment.

Specification:

```yaml
- moment:
    time: number_of_seconds
    mark: custom_message
    services:
      service_name_1:
         - service_event_1
         - service_event_2
         - ...
         - service_event_N
      service_name_2:
        - service_event_1
        - service_event_2
        - ...
        - service_event_N
      service_name_N:
        - service_event_1
        - service_event_2
        - ...
        - service_event_N
```

For `moment` events only the first to line are required, while the others are optional.

- `number_of_seconds` describes when to this event will happen (int)
- `custom_message` is a string. When `mark` is set then the experiment logs will include a `custom_message` timestamped at the moment. This line is optional.

__services__

`services` line and its contents are optional.

In this tag it is possible to define any number of `service_events` for every service in the experiment. If the `services` tag is present then at least one `service_event` for a `service` must be described.

There are the following types of `service_event`:

- [start](#start-anchor)
- [stop](#stop-anchor)
- [fault](#fault-anchor)

<a name="start-anchor"></a>
### start

This service_event will add more containers to the service.

Specification:

```yaml
- start:
    # exclusive option, either amount or percentage is defined
    amount: amount_number
    percentage: percentage_number **relative to ...**
```

- `amount_number` is an integer that represents the number of containers to add
- `percentage_number` is also an int (10 represents 10%), it will calculate the number of containers to add, based on the number of containers predicted to be alive. Decimals values are rounded up (3.4 rounds to 4)

If any of this values is negative the experiment will fail to start.

Examples of calculations for percentage:

1.  20% with 10 containers alive -> 2 containers added (0.20 * 10 = 2)
2.  20% with 11 containers alive -> 3 containers added (0.20 * 11 = 2.2 -> 3)
3. 100% with 10 containers alive -> 10 containers added (1.00 * 10 = 10)
4. 200% with 10 containers alive -> 20 containers added (2.00 * 10 = 20)


Only one of the options can be setup, either `amount` or `percentage`.

__Examples of `start`:__

```yaml
- start:
    amount: 15
```

15 Containers are added

```yaml
- start:
    percentage: 10
```

10% containers are added

<a name="stop-anchor"></a>
### stop

This service_event will shut down containers of the service. Initially the signal SIGTERM is sent and after a few seconds, if the signal was not effective, the system will resort to KILL.

Specification:

```yaml
- stop:
    # exclusive option, either amount, percentage or specific is defined
    amount: amount_number
    percentage: percentage_number
    specific:
        - ID_1
        - ID_2
        - ...
        - ID_N
```

- `amount_number` and `percentage_number` have the same characteristics as the `start` event_type, however `percentage_number` cannot be bigger than 100.
- `specific` describes the exact containers to stop. Its contents are an array that indicates each container to stop. The ids are integers. The first container in the service is the container 0, so all indexes must be bigger than 0.


__Examples of stop:__

```yaml
- stop:
    amount: 15
```

15 Containers are removed


```yaml
- stop:
    percentage: 10
```

10% containers are removed

```yaml
- stop:
    percentage: 100
```

All containers are removed

```yaml
- stop:
    specific:
        - 1
        - 3
        - 5
```
Containers 1, 3 and 5 are removed


<a name="fault-anchor"></a>
### Fault

 <!-- #[create an anchor](#anchors-in-markdown) -->

This service_event allows the injection of faults into the containers of services.

Specification:
```yaml
- fault:
    target:
        amount: amount_number
        percentage: percentage_number
        specific:
            - ID_1
            - ID_2
            - ...
            - ID_N
    fault_type
```

In `fault` both sections are required.
- `target` represents the containers in which to inject the fault. `amount`, `percentage` and `specific` have the same rules as presented in `stop` service_event.
- `fault_type` is what distinguishes the type of fault to inject. There are the following types of faults:
  - [KILL](#kill-anchor)
  - [Signal](#signal-anchor)
  - [CPU](#cpu-anchor)
  - [custom](#custom-anchor)


<a name="kill-anchor"></a>
### kill

This fault will kill containers of the service. For that a `SIGKILL` signal is sent to the main process of the container.

Specification:

```yaml
kill:
```

This fault_type has no arguments, just specify `kill` in the `fault_type` section.

__Example of kill:__

```yaml
- fault:
      target:
          amount: 2
      kill:
```

Two containers will be killed

**?? not sure if this is valid YAML, I will further investigate, if required will change to type: kill ??**

<a name="signal-anchor"></a>
### Signal

This fault will send a signal to containers.

Specification:
```yaml
signal:
    kills_container: yes / no
    signal: signal
```

- `kills_container` states whether or not this fault will kill container, it must be the string yes or no. This tells Faultsee to consider this container dead in future events.
- `signal` is a string and must be a valid regular POSIX signal:
    - SIGHUP   
    - SIGINT   
    - SIGQUIT  
    - SIGILL   
    - SIGTRAP  
    - SIGABRT  
    - SIGIOT   
    - SIGBUS   
    - SIGEMT   
    - SIGFPE   
    - SIGKILL  
    - SIGUSR1  
    - SIGSEGV  
    - SIGUSR2  
    - SIGPIPE  
    - SIGALRM  
    - SIGTERM  
    - SIGSTKFLT
    - SIGCHLD  
    - SIGCLD   
    - SIGCONT  
    - SIGSTOP  
    - SIGTSTP  
    - SIGTTIN  
    - SIGTTOU  
    - SIGURG   
    - SIGXCPU  
    - SIGXFSZ  
    - SIGVTALRM
    - SIGPROF  
    - SIGWINCH
    - SIGIO    
    - SIGPOLL  
    - SIGPWR   
    - SIGINFO  
    - SIGLOST  
    - SIGSYS   
    - SIGUNUSED


__Examples of signal:__
```yaml
- fault:
    target:
        percentage: 20
    signal:
        signal: SIGUSR1
        kills_container: yes
```

20% of the containers will receive the signal `SIGUSR1`, and they are not expected to be alive in the rest of the experiment.

```yaml
- fault:
    target:
        secific: [2, 4]
    signal:
        signal: SIGALRM
        kills_container: no
```

The containers number 2 and 4 will receive the signal SIGALRM. They will process the signal and are not expected to terminate.

<a name="cpu-anchor"></a>
### CPU

This fault will exhaust the CPU of the containers it targets.

Specification:
```yaml
cpu:
    duration: number_of_seconds
```

- `number_of_seconds` is the duration of the CPU exhaustion, must be a positive integer, otherwise it will fail.

__Example of cpu:__

```yaml
- fault:
      target:
          percentage: 20
      cpu:
          duration: 40
```

In this case 20% of the containers will have their CPU exhausted for 40 seconds

<a name="custom-anchor"></a>
### custom

Any script can be injected, as long as there is a executable that is able to interpret it
inside the container.

Specification:
```yaml
custom:
      kills_container: yes / no
      fault_file_name: fault_file_name
      fault_file_folder: fault_file_folder # default - /usr/lib/faultsee/
      fault_script_arguments: # default - empty array
          - arg_1
          - arg_2
          - ...
          - arg_N
      executable: executable # default - /bin/sh
      executable_arguments: # default - empty array
          - arg_1
          - arg_2
          - ...
          - arg_N
```

This fault has two required sections, `kills_container` and `fault_file_name`. The others have default values.

- `kills_container` states whether or not this fault will kill container, it must be the string `yes` or `no`. This tells Faultsee to consider this container dead in future events.
- `fault_file_name` is a string that reprents the name of the fault file
- `fault_file_folder` is a string. By default this value is /usr/lib/faultsee, this is the folder to which Faultsee copies all faults when setting a cluster
- `fault_script_arguments` is an array of strings, if the script requires arguments they can be described here. The default value is an empty array, and the order is preserved.
- `executable` is a string. It indicates what program will be used to interpret the script, default value is /bin/sh
- `executable_arguments` is an array of strings, if the executable requires arguments they can be described here. The default value is an empty array, and the order is preserved.

__Examples of custom:__

```yaml
- fault:
      target:
          amount: 5
      custom:
          kills_container: no
          fault_file_name: delete_files.py
          fault_file_folder: /myapp/
          fault_script_arguments:
              - all
              - -f
          executable: /usr/bin/python
          executable_arguments:
              - -u
```
This fault is the equivalent to run `/usr/bin/python -u /myapp/delete_files.py all -f` inside the container. This fault will be applied to 5 random containers of the service, and the containers are expected to survive.

```yaml
- fault:
      target:
          percentage: 15
      custom:
          kills_container: no
          fault_file_name: waste_memory
          fault_script_arguments:
              - 20
```

The fault waste_memory will be executed with the default values, with the argument 20. It is equivalent to `/bin/sh /usr/lib/faultsee/waste_memory 20`. It will be applied to 15% of the containers, and the containers are expected to survive.


```yaml
- fault:
      target:
          specific:
            - 1
      custom:
          kills_container: yes
          fault_file_name: stop_cassandra
```

This fault will be injected in the first container of the service, and the container will be considered dead from this event onwards. It is equivalent to `/bin/sh /usr/lib/faultsee/stop_cassandra`

<a name="tldr-anchor"></a>
# TL ; DR
One functional DUMMY example that does NOT contain ANY explanations is present in the following two files:
- [Services Configuration](./docker-compose.yaml)
- [Experiment](./experiment.yaml)

[Go back to top](#document-start)
<a name="document-end"></a>
