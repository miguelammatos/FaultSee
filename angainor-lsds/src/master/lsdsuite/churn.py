import json
import logging
import datetime
import string

import threading
import time
from os.path import join

from utils.bubble_sort import bubbleSort
from .experiment_step import EndStep, SignalStep, KillFault, CPUFault, StartReplicasStep, \
    StopReplicasStep, CustomFaultStep, FaultStep, BeginningStep

log = logging.getLogger(__name__)


class Churn(object):
    def __init__(self, spec):
        def error(name, msg):
            error = "Error in churn specification (service {name}): "
            error += msg
            return error.format(name=name)

        self.start_replicas = {}  # {<service>: <start-replicas>, ...}
        self.timeline = []  # = [(time, service, op, n, signal), ...]
        events = spec.get('events', {})
        # if 'synthetic' in experiment and 'real' in experiment:
        #     msg = error("only one of synthetic or real can be specified")
        #     log.error(msg)
        #     raise ValueError(msg)
        #
        # if any(mode not in supported_modes for mode, _ in experiment.items()):
        #     msg = error("Only ONE of ", supported_modes, " can be specified")
        #     log.error(msg)
        #     raise ValueError(msg)

        log.debug("Starting parse")
        log.debug("starting synthetic parse mode")
        self.timeline = self._parse_synthetic(events)
        # elif mode == 'real':
        #     log.debug("starting real parse mode")
        #     self.timeline = _parse_real("name", "churn['real']")

        # Sort by time ; maintain order otherwise
        def get_time(val):
            return val.time

        # bubbleSort used in order to control the sort algorithm
        # we will use bubble sort in master and slave
        # no need to worry about performance because this only runs once per round,
        # and with few items, generally already sorted
        bubbleSort(self.timeline, get_time)
        self.certify_moments_before_end(self.timeline)
        self._process_moments_amounts(self.timeline)

        log.debug("TimeLine")
        for event in self.timeline:
            log.debug("   " + str(event))

        log.debug("Parse completed")

    def process_stop(self, app, step, step_number, number_steps, interactive, dry_run):

        if not isinstance(step, StopReplicasStep):
            raise ValueError("Bad Step:", step)

        service_name = step.service_name
        number_replicas = step.number_replicas

        if not interactive:
            log.debug(
                "IGNORING Churn step %d/%d, stop: %s in %d instances of %s",
                step_number, number_steps, step.number_replicas, number_replicas, service_name)
            return

        log.info("Churn step %d/%d, STOP %d instances of %s",
                 step_number, number_steps, number_replicas, service_name)

        if dry_run:
            return

        service = app.service(name=service_name)
        service.rm(number_replicas)

    def process_add(self, app, step, step_number, number_steps, interactive, dry_run):
        if not isinstance(step, StartReplicasStep):
            raise ValueError("Misconstructed Step:", step)

        # even when running in non interactive mode, the master is the
        # one responsible for adding new replicas to a service

        service_name = step.service_name
        number_replicas = step.number_replicas

        log.info("Churn step %d/%d, adding %d instances of %s",
                 step_number, number_steps, number_replicas, service_name)
        if dry_run:
            return

        service = app.service(name=service_name)
        service.add(number_replicas, wait=False)

        step_id = step.get_id()
        self.register_id_processed(step_id)

    def process_end(self, app, step, step_number, number_steps, interactive, dry_run):
        # interactive cannot be ignored, it must always be executed
        log.info("Churn step %d/%d, end experiment", step_number, number_steps)
        for service in app.services:
            service.desired_replicas = 0
        step_id = step.get_id()
        self.register_id_processed(step_id)

    def process_fault(self, app, step, step_number, number_steps, interactive, dry_run):
        if not isinstance(step, FaultStep):
            raise ValueError("Misconstructed Step:", step)

        service_name = step.service_name
        number_replicas = step.number_replicas

        if not interactive:
            log.debug(
                "IGNORING Churn step %d/%d, Fault: %s in %d instances of %s",
                step_number, number_steps, step.operation,  number_replicas, service_name)
            return
        else:
            # oops.. TODO
            log.error("Implement Process Fault.. TODO.. FAULT NOT INJECTED")
            return
        # log.info("Churn step %d/%d, injecting %s (custom) in %d instances of %s",
        #          step_number, number_steps, step.fault_file_name, number_replicas, service_name)
        #
        # service = app.service(name=service_name)
        # service.custom_fault(number_replicas=number_replicas,
        #                      fault_details=fault_details, fault_arguments=fault_arguments, wait=False)

    def process_beginning(self, app, step, step_number, number_steps, interactive, dry_run):
        if not isinstance(step, BeginningStep):
            raise ValueError("Misconstructed Step:", step)
        log.info("Churn step %d/%d: Beginning Step Processed", step_number, number_steps)
        step_id = step.get_id()
        self.register_id_processed(step_id)



    # dictionary that helps select which function to call, depending on type of step
    process_functions = {
        'stop': process_stop,
        'start': process_add,
        'end': process_end,
        'beginning': process_beginning,
        'cpu': process_fault,
        'custom': process_fault,
        'signal': process_fault,
        'kill': process_fault,
    }

    # FIXME this should be tampered inside ENGINE, not spec
    # churn should be agnostic to docker yaml configurations
    # when we append kubernetes we might have problems here
    def apply_start(self, spec):
        services = spec.get('services')
        if not services:
            log.warning("No services specified in spec.")
            return

        for name, n in self.start_replicas.items():
            service = services.get(name)
            if not service:
                log.warning("Service %s in churn doesn't appear in spec.",
                            name)
                continue

            log.debug("Setting service %s start replicas to %d", name, n)
            service['deploy'] = service.get('deploy', {})
            service['deploy']['replicas'] = n

    # this function will arrange with slaves a start moment and will return at the start moment
    def _schedule_start(self, engine, start_in_N_seconds):
        no_error = False
        number_attempts = 0
        while not no_error and number_attempts < 5:
            if number_attempts > 0:
                start_in_N_seconds *= 2
            no_error = True
            number_attempts += 1
            # TODO create timeout
            # at the moment it waits for answer or socket close
            answer_list = engine.parallel_send_command("restart_round")
            for status, msg in answer_list:
                if status != 'ok':
                    log.warning("Error when trying to reset status in slave: " + str(msg))
                    no_error = False
            if not no_error:
                continue

            start_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=start_in_N_seconds)
            log.info("Trying to start the experiment round @ " + str(start_date))
            start_date_string = start_date.astimezone().isoformat()

            answer_list = engine.parallel_send_command("start_run_at", datetime=start_date_string)
            for status, msg in answer_list:
                if status != 'ok':
                    log.warning("Error when trying to schedule start moment in slave: " + str(msg))
                    no_error = False

            if not no_error:
                continue

            now_date = datetime.datetime.now(datetime.timezone.utc)
            log.debug("Planning start @ " + start_date.__str__())
            missing_time = start_date - now_date
            sleep_seconds = missing_time.total_seconds()
            if sleep_seconds < 0:
                answer_list = engine.parallel_send_command("cancel_run")
                for status, msg in answer_list:
                    if status != 'ok':
                        error_message = "Cancel Round Failed. The experiment is out of control. Please consider turning restarting the cluster. error: " + str(msg)
                        log.error(error_message)
                        raise ValueError(error_message)
                # we missed our deadline ..
                log.warning("Error while scheduling start of next run, we missed start moment")
                no_error = False
                # duplicate the time window to start the experiment
                continue

            else:
                log.info("Sleeping: " + str(sleep_seconds) + " until round start")
                time.sleep(sleep_seconds)

        if not no_error:
            error_message = "Failed to start run"
            log.error(error_message)
            raise ValueError(error_message)

    def register_id_processed(self, id):
        self.processed_ids += [id]

    def reset_processed_ids(self):
        self.processed_ids = []

    def get_processed_ids(self):
        return self.processed_ids

    def start(self, engine, app, dry_run=False, start_in_N_seconds=2):
        if dry_run:
            app.send_dry_run_to_all_nodes()
        else:
            self._schedule_start(engine, start_in_N_seconds)
        # else:
        #     app.send_start_to_all_nodes()

        last_t = 0
        n_steps = len(self.timeline)
        total_time = self.timeline[-1].time
        log.info("Starting experiment: " + str(datetime.datetime.now()))
        log.info("Churn steps: %d, duration %ds", n_steps, total_time)
        self.reset_processed_ids()
        for step_number, step in enumerate(self.timeline, 1):
            step_time = step.time
            operation = step.operation
            sleep = max(0, step_time - last_t)
            last_t = step_time
            now_date = datetime.datetime.now()
            next_step_date = now_date + datetime.timedelta(seconds=sleep)
            log.info("%s Churn step %d/%d, sleeping for %ds until %s",
                     now_date, step_number, n_steps, sleep,
                     next_step_date)

            if dry_run:
                continue

            time.sleep(sleep)
            if operation not in self.process_functions.keys():
                # else:
                log.warning("Churn step %d, ignoring UNSUPPORTED step: %s",
                            step_number, step)
                continue

            function = self.process_functions[operation]
            t = threading.Thread(target=function,
                                 args=(self, app, step, step_number,
                                       n_steps, False, dry_run),
                                 name=str(step))
            t.start()
            # function(app, step, step_number, n_steps, interactive=False, dry_run)

    def stop(self, engine, experiment_results_folder):
        master_processed_ids = self.get_processed_ids()
        events, maxID, hosts_list = engine.get_processed_events()
        master_container_name = "faultsee-master-container"
        hosts_list += [master_container_name]


        number_of_hosts = len(hosts_list)
        skip_host_print = number_of_hosts > 15
        if skip_host_print:
            log.info("too many hosts, will not print processed events information, check file for all the details")


        # keys A1, B2, C3 ...
        hosts_key = {}
        for i, host in enumerate(hosts_list):
            key = string.ascii_uppercase[i] + str(i + 1)
            hosts_key[host] = key

        if not skip_host_print:
            print("Hosts Keys")
            for host, key in hosts_key.items():
                print("   ", key, " -> ", host)

        # header
        print(" ", "{:3s}".format("IDS"), end="")
        if not skip_host_print:
            print(" ||| ", "{:47s}".format("Hosts"), end="")
        print(" ||| ", "Event Action")
        print(" ", "_"*3, "_"*5, "_"*47, "_"*5, "_"*15)

        not_processed_events = []

        id = 0
        while id <= maxID:
            info = events.get(id, None)
            master_processed_this_id = id in master_processed_ids
            at_least_one = master_processed_this_id
            hosts_string = ""
            message_string = ""

            if master_processed_this_id and not skip_host_print:
                hosts_string += hosts_key[master_container_name]

            # check if processed
            # build strings to print
            if info is not None:
                for host in info:
                    if host["Processed"]:
                        if not skip_host_print:
                            hosts_string += (" | " if at_least_one else "") + hosts_key[host["Host"]]
                        at_least_one = True
                    host_msg = host.get("Action")
                    if host_msg is not None:
                        message_string = host_msg

                master_container_json_info = {
                                                 "Host": master_container_name,
                                                 "Action": message_string,
                                                 "Processed": master_processed_this_id
                                             },
                # add info so json dump contains master node info
                # master information for console line is processed before "if info is not None"
                info += master_container_json_info
                events[id] = info
            else:
                # id did not exist in events before, appending information
                events[id] = {
                     "Host": master_container_name,
                     "Action": "... Missing details on this event",
                     "Processed": master_processed_this_id
                }

            if at_least_one:
                hosts = hosts_string
            else:
                hosts = "---- Not Processed ----"
                not_processed_events += [id]


            # print the stuff
            print(" ", "{:3d}".format(id), end="")
            if not skip_host_print:
                print(" ||| ", "{:47s}".format(hosts), end="")
            if info is not None:
                print(" ||| ", message_string)
            else:
                print(" ||| ", "... Missing details on this event")

            # new cycle
            id += 1


        # write to file
        path = join(experiment_results_folder, "processed_events.log")
        events["hosts"] = hosts_list
        with open(path, 'w') as outfile:
            json.dump(events, outfile)

        if len(not_processed_events) > 0 :
            log.error("At least one of the events was not processed.. NOT PROCESSED:" + str(not_processed_events))


    def certify_moments_before_end(self, steps):
        # make sure last step is END
        if not isinstance(steps[-1], EndStep):
            error_message = "Last Moment must be the end"
            log.error(error_message)
            raise ValueError(error_message)

        index = 0
        while index < (len(steps) - 1):
            step = steps[index]
            if isinstance(step, EndStep):
                error_message = "Only the last moment can be the end"
                log.error(error_message)
                raise ValueError(error_message)
            index += 1

    # assumes faults are already sorted
    def _process_moments_amounts(self, faults):
        current_replicas = {}
        for name, start_amount in self.start_replicas.items():
            current_replicas[name] = start_amount

        log.debug("Processing Moments Amounts")
        self.current_id = 0
        for fault in faults:
            log.debug("")
            log.debug("----------------------------------")
            log.debug("Before Moment: %s", current_replicas)
            fault.calculate_service_amounts(current_replicas)
            fault.set_id(self.current_id)
            amount_ids = fault.consumes_ids()
            self.current_id += amount_ids
            log.debug("Moment: %s", fault)
            log.debug("After Moment: %s", current_replicas)
            log.debug("----------------------------------")


    def _parse_synthetic(self, steps):
        # self.timeline += service['steps']
        # self.timeline.append((service['end'], name, 'end', 0, None))

        def parse_n(n):
            if type(n) == str and n[-1] == '%':
                n = float(n[:-1]) / 100
                if n < 0 or n > 1:
                    raise ValueError("N must be between 0% and 100%")
            elif type(n) == float:
                raise ValueError("N must be integer or percentage")
            else:
                n = int(n)
                if n < 0:
                    raise ValueError("N must be >= 0")
            return n

        timeline = []
        # service = {'steps': []}
        end_is_defined = False
        for step_number, step in enumerate(steps, 1):
            try:
                if end_is_defined:
                    raise ValueError("no further steps allowed after end")

                elif 'moment' in step:
                    faults = _parse_moment(step)
                    timeline += faults
                elif 'beginning' in step:
                    for service_name, amount_start in step["beginning"].items():
                        self.start_replicas[service_name] = int(amount_start)
                    start_step = BeginningStep(0)
                    timeline.append(start_step)
                    continue

                elif 'end' in step:
                    end_is_defined = True
                    end_time = int(step['end'])
                    endStep = EndStep(end_time)
                    timeline.append(endStep)
                    # TODO create END step
                    continue
                else:
                    msg = "Unsupported step: " + str(step)
                    log.error(msg)
                    raise ValueError(msg)

            except ValueError as e:
                error = "Error in churn specification (step number {step_number}) step: {step} : "
                error = error.format(step=step, step_number=step_number)
                error += str(e)
                raise ValueError(error)

        if not end_is_defined:
            error = "Error in churn specification: end not specified"
            raise ValueError(error)
        log.debug("Parse Complete, %d steps created", len(timeline))
        return timeline


def _parse_moment(step):
    moment = step['moment']

    fault_time = moment.get('time', None)
    if fault_time is None:
        raise ValueError("time must be specified in a moment")

    faults = []
    if moment.get('mark', None):
        mark_step = BeginningStep(fault_time)
        faults.append(mark_step)

    if moment.get('services', None) is not None:
        for service_name, service_events in moment['services'].items():
            for event in service_events:
                for fault_type, fault_details in event.items():
                    if fault_type == "fault":
                        fault = _parse_fault(fault_details, fault_time, service_name)
                    else:
                        possibilities = {
                            "start": StartReplicasStep,
                            "stop": StopReplicasStep,
                        }
                        event_type = possibilities.get(fault_type, None)
                        if event_type is None:
                            raise ValueError(
                                fault_type, "not supported as a moment, possibilities: " + str(possibilities.keys()))
                        fault = event_type(fault_time, service_name, fault_details)
                    faults.append(fault)
    else:
        # make sure there is at least something, like "mark"
        #
        # EXAMPLE
        # mark: end_of_some_stuff
        if moment.get('mark', None) is None:
            raise ValueError("Invalid Moment. Reason: Empty. Moment: ", moment)
    return faults


def _parse_fault(fault_details, fault_time, service_name):
    possibilities = {
        "kill": KillFault,
        "signal": SignalStep,
        "custom": CustomFaultStep,
        "cpu": CPUFault
    }
    for section, content in fault_details.items():
        fault_type = possibilities.get(section, None)
        if fault_type is None:
            continue
        else:
            fault = fault_type(fault_time, service_name, fault_details)
            return fault
    raise ValueError(fault_details, "Fault not supported, possibilities: " + str(possibilities.keys()))


def _parse_real(name, spec):
    msg = "Currently we do not support Real format TODO FIXME"
    log.error(msg)
    raise ValueError(msg)
    import sqlite3

    database = spec.get('database')
    if not database:
        raise ValueError("Real churn spec must have database")

    time_factor = spec.get('time_factor', 1)
    time_step = spec.get('time_step', 10)
    max_duration = spec.get('max_duration')
    signal = spec.get('signal')

    sql = sqlite3.connect(database)
    cur = sql.cursor()
    # HUGE performance boost
    cur.execute(r"CREATE INDEX IF NOT EXISTS start_time_index "
                "ON event_trace (event_start_time)")
    cur.fetchone()

    cur.execute(r"SELECT MIN(event_start_time), MAX(event_start_time) "
                "FROM event_trace")
    min_time, max_time = map(int, cur.fetchone())

    cur.execute("""
    SELECT DISTINCT node_id FROM event_trace
    WHERE event_start_time <= ?
    ORDER BY node_id""",
                [max_time])

    node_ids = [x[0] for x in cur.fetchall()]
    nodes = dict(zip(node_ids, range(len(node_ids))))

    end_time = (max_time - min_time) / time_factor / time_step
    end_time = int(end_time + 1) * time_step
    end_time = min(end_time, max_duration)

    service = {'start': 0, 'end': end_time, 'steps': []}

    step = time_step * time_factor
    for i, t in enumerate(range(min_time, max_time+step+1, step)):
        time = (i+1) * time_step
        if max_duration and time > max_duration:
            break

        cur.execute("""
        SELECT node_id, event_type FROM event_trace
        WHERE event_start_time >= ?
        AND event_start_time < ?
        ORDER BY node_id, event_start_time""",
                    (t, t+step))

        events = cur.fetchall()
        kill, add = [], []
        for node in {x[0] for x in events}:
            ups = sum(1 for x in events if x[0] == node and x[1] == 1)
            downs = sum(1 for x in events if x[0] == node and x[1] == 0)

            if ups > downs:
                add.append(nodes[node])
            if downs > ups:
                kill.append(nodes[node])

        if kill:
            service['steps'].append((time, name, 'kill', kill, signal))
        if add:
            service['steps'].append((time, name, 'add', add, None))

    return service
