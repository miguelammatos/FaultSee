#!/usr/bin/env python
import json
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pprint
import inspect
import re
from datetime import timedelta
from termcolor import colored

debug_print_logs = False
parse_latency_data = True
x_upper_limit = 4300


LATENCY_UPPER_LIMIT = 10000
# uncomment  to unset option
# LATENCY_UPPER_LIMIT = -1

pp = pprint.PrettyPrinter(indent=4)

# "[Operation], time_as_ms_since_start, #operations/interval"
START_OVERALL_LINE = re.compile("^\[OVERALL\]\,\sRunTime\(ms\)\,\s(\d+)$")
# [READ], 1000, 1922.5124555160141
READ_STATUS_LINE = re.compile("^\[READ\]\,\s(\d+)\,\s(\d+\.\d+)$")
# "[UPDATE], 0, 3096.2569832402237"
UPDATE_STATUS_LINE = re.compile("^\[UPDATE\]\,\s(\d+)\,\s(\d+\.\d+)$")
# " has finished"
END_STATUS_LINE = re.compile("^\shas\sfinished$")
# "2019-05-31 13:17:06:245 1440 sec: 23863825 operations; 16202.6 current ops/sec; est completion in 9  minutes [READ AverageLatency(us)=782.17] [UPDATE AverageLatency(us)=444.25]"
STATUS_EVERY_10_LINE = re.compile(".*\d+\:\d+\:\d+\:\d+\s(\d+)\ssec\:\s(\d+)\soperations\;\s(\d+\.\d+)\scurrent.*\[READ\sAverageLatency\(us\)\=.*$")


# Status Line
# STATUS_EVERY_10_LINE = re.compile("(\d+)\ssec\:\s(\d+)\soperations")
# 2019-05-31 13:16:16:245 1390 sec: 23051290 operations; 16524.2 current ops/sec; est completion in 10 minutes [READ AverageLatency(us)=761.33] [UPDATE AverageLatency(us)=440.51


def load(path):
    def read(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                split = line.split('\t', 2)
                while len(split) < 3:
                    split.append("")
                time, id, msg = split
                time, subject = time.split(' ', 1)
                subject = subject[1:-1]  # remove brackets

                data = dict(time=time, subject=subject, id=id)

                if subject == 'LOG':
                    data['log'] = msg

                if subject == 'EVENT':
                    msg = json.loads(msg)
                    if msg['Type'] != 'container':
                        continue

                    attr = msg['Actor']['Attributes']
                    data['service'] = attr.get('com.docker.swarm.service.name')
                    data['signal'] = attr.get('signal')
                    data['status'] = msg['status']

                if subject == 'STATS':
                    msg = json.loads(msg)

                    preread = msg['preread']
                    if preread.startswith("0001"):
                        cpu = 0
                    else:
                        dt = (pd.to_datetime(msg['read'])
                              - pd.to_datetime(preread)).to_timedelta64()
                        dt = dt.astype('int')
                        cpu = (msg['cpu_stats']['cpu_usage']['total_usage']
                               - msg['precpu_stats']['cpu_usage']['total_usage'])
                        # n=len(msg['cpu_stats']['cpu_usage']['percpu_usage'])
                        cpu /= dt

                    data['cpu'] = cpu
                    data['mem'] = msg['memory_stats']['usage']
                    data.update(msg['networks']['eth0'])

                if subject == 'HOST':
                    try:
                        msg = json.loads(msg)
                        data['cpu'] = msg['cpuPercent'][0] / 100
                        data['mem'] = msg['mem']['usedPercent'] / 100
                    except Exception as e:
                        print(msg)
                        raise e

                if subject == 'MARK':
                    try:
                        msg = json.loads(msg)
                        if msg['type'] == 'benchmark':
                            data['mark'] = msg['status']

                        if msg['type'] == 'churn':
                            data['mark'] = 'churn'
                            op, num = msg['op'], msg['num']
                            data['service'] = msg['service']
                            if op != 'end':
                                op += ":" + str(num)
                            data['churn'] = op

                        if msg['type'] == 'operation':
                            data['mark'] = msg['operation']
                    except:
                        data['mark'] = 'event'
                        # ignore..
                        pass

                yield data

    df = pd.DataFrame(read(path))
    # print(df.time)
    df.time = pd.to_datetime(df.time)
    df = df.sort_values(by='time')
    print("sorted by time")

    start = df[df.mark == 'start'].iloc[0].time
    stop = df[df.mark == 'stop'].iloc[-1].time

    df = df[(df.time >= start) & (df.time <= stop)]
    df['dt'] = df.time - df.time.min()

    return df


def concatenate_all_axes(*all_axes):
    result = []
    for axe in all_axes:
        the_list = [x for x in axe]
        result = result + the_list
    return result  # + lista_3


def concatenate_all_figs(*all_axes):
    return all_axes


def formate_time_log(time):
    if time.days > 0:
        return str(time)
    else:
        tot_seconds = time.total_seconds()
        hours, remainder = divmod(tot_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return '{:02}H {:02}:{:02}'.format(int(hours), int(minutes), int(seconds))


def print_service_logs(df, service_name):
    if not debug_print_logs:
        return
    service_ids = set(df[df.service == service_name].id.unique())

    print("LOGS OF SERVICE: ", service_name)
    logs = df[(df.subject == 'LOG') & df.id.isin(service_ids)]
    time_as_list = list(logs['dt'])
    service_id_as_list = list(logs['id'])
    for index, line in enumerate(logs['log']):
        print("  ", formate_time_log(time_as_list[index]), "->",
              service_id_as_list[index][:10] + ":", line)
        # print("at ", splitted[1],"ms ->", splitted[2] )


def create_dataframe_reads_and_writes(logs, containerID, read_index, write_index, operation_index, r_requests, w_requests, ops_requests):
    started = False
    ended = True
    logs = logs[['dt', 'log', 'service']]
    as_list = list(logs['dt'])
    # as_list_service = list(logs['service'])
    for index, line in enumerate(logs['log']):
        # print(line)
        # read until:  [OVERALL], RunTime(ms), 175003
        # this line has the total_runtime and is produced at end_time
        # start_time = end_dime - total_runtime
        if START_OVERALL_LINE.match(line):
            print(line)
            if started:
                print("   ", "!!it started again")
            if not ended:
                print("   ", "!!it not ended yet..")
            started = True
            ended = False
            splitted = re.split(START_OVERALL_LINE, line)
            print("series has started")
            # print(index, as_list[index], line)
            # print("time_since_start = ", splitted[1], "ms")
            print("start_time", as_list[index]
                  - timedelta(milliseconds=int(splitted[1])))
            print("end_time", as_list[index])
            start_time = as_list[index] - \
                timedelta(milliseconds=int(splitted[1]))
            end_time = as_list[index]
            # start_time =
            # end_time =
        if END_STATUS_LINE.match(line):
            if not started:
                print("   ", "!!it ended without start")
            if ended:
                print("   ", "!!it ended again..")
            ended = True
            # splitted = re.split(END_STATUS_LINE, line)
            print("series has ended")
        if READ_STATUS_LINE.match(line):
            if ended:
                print("   ", "!! read after end")
            if not started:
                print("   ", "!! read before start")
            splitted = re.split(READ_STATUS_LINE, line)
            # if splitted[1] == "0":
            #     continue
            # print("at ", splitted[1],"ms ->", splitted[2] )
            r_requests.loc[read_index] = [
                start_time + timedelta(milliseconds=int(splitted[1])), float(splitted[2]), containerID]
            read_index += 1
        if UPDATE_STATUS_LINE.match(line):
            if ended:
                print("   ", "!! write after end")
            if not started:
                print("   ", "!! write before start")
            splitted = re.split(UPDATE_STATUS_LINE, line)
            # if splitted[1] == "0":
            #     continue
            # print("at ", splitted[1],"ms ->", splitted[2] )
            w_requests.loc[write_index] = [
                start_time + timedelta(milliseconds=int(splitted[1])), float(splitted[2]), containerID]
            write_index += 1

        if STATUS_EVERY_10_LINE.match(line):
            status_moment = as_list[index]
            splitted = re.split(STATUS_EVERY_10_LINE, line)
            current_ops = float(splitted[3])

            ops_requests.loc[operation_index] = [status_moment, current_ops, containerID]
            operation_index += 1

    return read_index, write_index, operation_index


def plot_latency_grouped_by_time(axe, label, data_label, freq, requests):
    requests = requests.set_index('dt')
    requests = requests.groupby(pd.Grouper(freq=freq)).mean()
    requests['dt'] = requests.index
    dt = requests.dt.dt.total_seconds()
    axe.plot(dt, requests[data_label], linestyle='dashed', label=label)
def plot_latency(axe, label, data_label, requests):
    requests = requests.set_index('dt')
    requests['dt'] = requests.index

    dt = requests.dt.dt.total_seconds()
    axe.plot(dt, requests[data_label], linestyle='dashed', label=label)

def process_container_stats_plot(df, container_id, axe):
    # Calculate per-instance resource stats

    stats = df[(df.subject == 'STATS') & (df.id == container_id)]
    stats = stats[['dt', 'id', 'cpu', 'mem', 'rx_bytes', 'tx_bytes']]

    # process bandwidth
    diff_sec = stats.dt.dt.total_seconds().diff()
    stats.loc[stats.id == id, 'rx_bw'] = stats.rx_bytes.diff() / diff_sec
    stats.loc[stats.id == id, 'tx_bw'] = stats.tx_bytes.diff() / diff_sec
    stats.set_index("dt")
    dt = stats.dt.dt.total_seconds()

    # name = 'Manager Node'
    axe.plot(dt, stats.cpu * 100, label="CPU - " + container_id[:8] )
    axe.plot(dt, stats.rx_bw / 1024 / 1024, label="Received -" + container_id[:8])
    axe.plot(dt, stats.tx_bw / 1024 / 1024, label="Sent - " + container_id[:8])
    # axe.plot(dt, stats.mem * 100, label="MEM - " + container_id[:8])

    axe.legend()



def process_service_stats_plot(df, service_ids, axe_cpu, axe_bandwidth):

    # Calculate per-instance resource stats
    stats = df[(df.subject == 'STATS') & df.id.isin(service_ids)]
    stats = stats[['dt', 'id', 'cpu', 'mem', 'rx_bytes', 'tx_bytes']]

    # processes badtwith data
    def treat_instance(stats, id, axe_cpu, axe_bandwidth):
        s = stats[stats.id == id]
        dt = s.dt.dt.total_seconds().diff()
        stats.loc[stats.id == id, 'rx_bw'] = s.rx_bytes.diff() / dt
        stats.loc[stats.id == id, 'tx_bw'] = s.tx_bytes.diff() / dt

    def plot_instance(stats, id, axe_cpu, axe_bandwidth):
        st = stats[stats.id == id]
        # rq = requests[requests.id == id]
        # ax_req.plot(rq.dt.dt.total_seconds(), rq.requests)
        dt = st.dt.dt.total_seconds()
        axe_cpu.plot(dt, st.cpu * 100)
        axe_bandwidth.plot(dt, st.rx_bw / 1024 / 1024, label="", ls=':')
        axe_bandwidth.plot(dt, st.tx_bw / 1024 / 1024, label="")

    def plot_individual_cpu(stats, id, axe_cpu):
        st = stats[stats.id == id]
        # rq = requests[requests.id == id]
        # ax_req.plot(rq.dt.dt.total_seconds(), rq.requests)
        dt = st.dt.dt.total_seconds()
        axe_cpu.plot(dt, st.cpu * 100, label="CPU - " + str(id[:8]), linestyle='dashed')
    # axe_bandwidth.plot(dt, st.rx_bw / 1024 / 1024,
    #                    label="Received", ls=':')
    # axe_bandwidth.plot(dt, st.tx_bw / 1024 / 1024, label="Transmitted")
    # compute bytes/s for each instance
    for id in stats.id.unique():
        treat_instance(stats, id, axe_cpu, axe_bandwidth)
        # plot_individual_cpu(stats, id, axe_cpu)
        # plot_instance(stats, id, axe_cpu, axe_bandwidth)

    stats = stats.set_index('dt')
    stats = stats.groupby(pd.Grouper(freq='5S')).mean()
    stats['dt'] = stats.index
    dt = stats.dt.dt.total_seconds()
    # name = 'Manager Node'
    axe_cpu.plot(dt, stats.cpu * 100, label="MEAN CPU")
    axe_bandwidth.plot(dt, stats.rx_bw / 1024
                       / 1024, label="MEAN Received")
    axe_bandwidth.plot(dt, stats.tx_bw / 1024 / 1024,
                       label="MEAN Sent")
    axe_bandwidth.legend()
    axe_cpu.legend()


def process_service_instances_plot(df, service_ids, axe, label="", linestyle=""):
    # compute up/down events for service
    events = df[df.id.isin(service_ids) & df.status.isin(
        ['start', 'die'])].copy()
    events.status = ((events.status == 'start').astype('int')
                     - (events.status == 'die').astype('int'))
    events['instances'] = events.status.cumsum()
    events['i'] = 0
    for i, id in enumerate(events.id.unique()):
        events.loc[events.id == id, 'i'] = i + 1

    # events = events[['dt', 'id', 'i', 'status', 'instances']]
    events = events[['dt', 'instances']]

    # make instances line start on second zero
    zero_on_start = pd.DataFrame(
        {"dt": [timedelta(milliseconds=0)], "instances": [0]})
    zero_on_start = zero_on_start.append(events)

    # create plot
    instances = zero_on_start.set_index('dt')
    instances = instances.resample('S').last().ffill()
    instances['dt'] = instances.index
    axe.plot(instances.dt.dt.total_seconds(),
             instances.instances, label=label, linestyle=linestyle)


def process_node_plot(df, axe):

    nodes = df[df.subject == 'HOST']
    nodes = nodes[['dt', 'id', 'cpu', 'mem']]

    colors = matplotlib.rcParams['axes.prop_cycle']
    colors = [c['color'] for c in colors]
    manager = list(nodes.id.unique())[0]
    # stats_manager, stats_workers = nodes[nodes.id
    #                                      == manager], nodes[nodes.id != manager]

    def plot_type_host(axe, stats, name, lw, ls):
        stats = stats.set_index('dt')
        stats = stats.groupby(pd.Grouper(freq='5S')).mean()
        stats['dt'] = stats.index
        dt = stats.dt.dt.total_seconds()
        # name = 'Manager Node'
        axe.plot(dt, stats.cpu * 100, label=name + " CPU", lw=lw)
        axe.plot(dt, stats.mem * 100,
                 label=name + " MEM", lw=lw, ls=ls)

    # plot_type_host(axe, stats_manager, "Manager node", 2, ":")
    # plot_type_host(axe, stats_workers, 'Workers Average', 1, "--")
    plot_type_host(axe, nodes, 'Hosts Average', 1, "--")
    axe.legend()


def process_marks_plot(df, axes):
    # start/stop/churn marks
    marks = df[df.subject == 'MARK']
    # only keep marks of one node, they're all the same anyway

    marks = marks[marks.id == marks.id.iloc[0]]
    marks = marks[marks.mark == 'event']

    # marks = marks[['dt', 'mark', 'service', 'churn']]
    # # put marks in all graphs
    for _, mark in marks.iterrows():
        # # filter marks of only one service
        # if mark.service != 'siege':
        #     continue
        for ax in axes:
            ax.axvline(mark['dt'].total_seconds(),
                       color=(0, 0, 0, .1), ls='--')


def process(df, title=None):
    print(" Services in Experiment: " + str(df.service.unique()))

    # create PDF first page
    first_fig, first_axes = plt.subplots(
        nrows=4, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    axe_cassandra_instances, axe_cassandra_cpu, axe_cassandra_bandwidth, axe_nodes = first_axes

    # create PDF second page - Both Clients mean
    second_fig, second_axes = plt.subplots(
        nrows=4, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    both_axe_1s, both_axe_3s, both_axe_5s, both_axe_debit = second_axes

    # create PDF third page - Only Clients Separated
    third_fig, third_axes = plt.subplots(
        nrows=4, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    individual_axe_1s, individual_axe_3s, individual_axe_5s, individual_axe_debit = third_axes

    cassandra_ids = set(df[df.service == 'cassandra'].id.unique())

    # create PDF forth page - Stats for cassandra containers
    fourth_fig, fourth_axes = plt.subplots(
        nrows=len(cassandra_ids), ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    # create PDF forth page - Stats for cassandra containers
    fifth_fig, fifth_axes = plt.subplots(
        nrows=1, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    # create PDF forth page - Stats for cassandra containers
    sixth_fig, sixth_axes = plt.subplots(
        nrows=1, ncols=1, sharex=True, figsize=(10, 12), dpi=300)

    # print(sixth_axes)
    # print(fifth_axes)
    # a, b = fifth_axes
    # print(a)
    # print(b)

    axe_cassandra_instances = sixth_axes
    both_axe_debit = fifth_axes
    # _, axe_cassandra_instances = sixth_axes

    service_name = "cassandra"

    # Set titles
    # axe_cassandra_instances.set_title(
    #     r"Number of " + service_name + " instances")
    axe_cassandra_cpu.set_title("MEAN " + service_name+r" CPU usage [\%]")
    axe_cassandra_bandwidth.set_title(service_name+r" bandwidth usage [MiB/s]")
    axe_nodes.set_title(r"Node CPU and memory usage [\%]")
    both_axe_1s.set_title(r"Mean Workload Latency - Group by 1 seconds")
    both_axe_3s.set_title(r"Mean Workload Latency - Group by 3 seconds")
    both_axe_5s.set_title(r"Mean Workload Latency - Group by 5 seconds")
    # both_axe_debit.set_title(r"Mean Workload Debit - Sampled every 10 seconds")

    individual_axe_1s.set_title(r"Individual Workload Latency - Group by 1 seconds")
    individual_axe_3s.set_title(r"Individual Workload Latency - Group by 3 seconds")
    individual_axe_5s.set_title(r"Individual Workload Latency - Group by 5 seconds")
    individual_axe_debit.set_title(r"Individual Workload Debit - Sampled every 10 seconds")


    # axe_ycsbal_instances.set_title(
    #     r"Number of " + "work A - Load" + " instances")
    # axe_ycsbar_instances.set_title(
    #     r"Number of " + "work A - Run" + " instances")
    # axe_ycsbbr_instances.set_title(
    #     r"Number of " + "work B - Run" + " instances")
    # axe_setup.set_title(r"Number of " + "axe setup" + " instances")

    axes = concatenate_all_axes(first_axes, second_axes, third_axes, fourth_axes, [fifth_axes], [sixth_axes])
    all_figs = concatenate_all_figs(first_fig, second_fig, third_fig, fourth_fig, fifth_fig, sixth_fig)
    # for fig in all_figs:
    #     fig.tight_layout()
    #     fig.subplots_adjust(top=.93, bottom=.07)

    # set lenght graph (time -> x_axis) in all axes
    for ax in axes:
        ax.yaxis.grid()
        if x_upper_limit > 0:
            ax.set_xlim(0, x_upper_limit)
        else:
            ax.set_xlim(0, df.dt.dt.total_seconds().max())
        # ax.set_ylim(bottom=0)
        ax.set_xlabel("Tempo [s]")

    axe_cassandra_instances.set_ylabel("Número Contentores")
    both_axe_debit.set_ylabel("Número Operações")
    sixth_fig.subplots_adjust(top=.90, bottom=.75)
    fifth_fig.subplots_adjust(top=.90, bottom=.75)

    # sixth_fig.yticks([1, 2, 3, 4, 5])

    # axe_reads.set_ylim(bottom=0, top=6000)
    # axe_reads.set_xlim(auto=True)

    # print(type(df))
    cassandra_ids = set(df[df.service == 'cassandra'].id.unique())
    ycsbal_ids = set(df[df.service == 'ycsbal'].id.unique())
    ycsbar_ids = set(df[df.service == 'ycsbar'].id.unique())
    ycsbbr_ids = set(df[df.service == 'ycsbbr'].id.unique())
    setup_service_ids = set(df[df.service == 'setup-service'].id.unique())

    # print_service_logs(df, "ycsbar")
    print_service_logs(df, "cassandra")

    # calculate number of requests served
    comulative_r_requests = pd.DataFrame(columns=["dt", "read", "containerID"])
    comulative_w_requests = pd.DataFrame(columns=["dt", "write", "containerID"])
    operations_requests = pd.DataFrame(columns=["dt", "ops", "containerID"])
    read_index = 0
    write_index = 0
    operation_index = 0

    # print(df[df.service == "ycsbar"][["service","id"]].id.unique())
    print(df[(df.subject == 'LOG')].id.unique())
    for service_ids, name in [(ycsbal_ids, "Load A"), (ycsbar_ids, "Run A - 50r/50w"), (ycsbbr_ids, "Run B - 95r/5w")]:
        print("")
        print(name)
        logs = pd.DataFrame()
        for containerID in service_ids:
            print("Container: ", containerID)

            logs = df[(df.subject == 'LOG')]
            logs = logs[logs.id == containerID]
            read_index, write_index, operation_index = create_dataframe_reads_and_writes(
                # logs, read_index, write_index, r_requests, w_requests)
                logs, containerID, read_index, write_index, operation_index, comulative_r_requests, comulative_w_requests, operations_requests)

    if parse_latency_data:
        print("parsing latency data")

        comulative_sum = pd.DataFrame()
        comulative_sum["sum"] = comulative_r_requests.read + \
            comulative_w_requests.write
        comulative_sum["dt"] = comulative_r_requests["dt"]
        comulative_sum["containerID"] = comulative_r_requests["containerID"]
        print("shape read", comulative_r_requests.shape)
        print("shape write", comulative_w_requests.shape)
        print("shape ops", operations_requests.shape)
        print("shape sum", comulative_sum.shape)
        # for axe, freq in [(axe_1s, "1S"), (axe_3s, "3S"), (axe_5s, "5S"), (axe_10s, "10S")]:
        for axe, freq in [\
                (both_axe_1s, "1S"), \
                (both_axe_3s, "3S"), \
                (both_axe_5s, "5S")]:
            # plot_latency_grouped_by_time(
            #     axe, "latency - all - write - " + freq, "write", freq, comulative_w_requests.copy()[["dt","write"]])
            # plot_latency_grouped_by_time(
            #     axe, "latency - all - read - " + freq, "read", freq, comulative_r_requests.copy()[["dt","read"]])
            plot_latency_grouped_by_time(
                axe, "latency - all - sum - " + freq, "sum", freq, comulative_sum.copy()[["dt","sum"]])
            axe.set_ylabel("Group by " + freq)
            axe.legend()
            if LATENCY_UPPER_LIMIT > 0:
                axe.set_ylim(1000, LATENCY_UPPER_LIMIT)
        axe = both_axe_debit
        # color = 'tab:red'
        # axe_10s_other.plot(t, data2, color=color)
        # axe_10s_other.tick_params(axis='y', labelcolor=color)

        all_operations = operations_requests.copy()
        all_operations = all_operations[["dt","ops"]]
        all_operations = all_operations.set_index('dt')
        all_operations = all_operations.groupby(pd.Grouper(freq="10S")).mean()
        all_operations.reset_index()
        all_operations['dt'] = all_operations.index
        plot_latency(axe, "debit - 10s", "ops", all_operations)

        for containerID in ycsbar_ids:
            write = comulative_w_requests.copy()
            read = comulative_r_requests.copy()
            sum = comulative_sum.copy()
            operations = operations_requests.copy()

            for axe, freq in [\
                    (individual_axe_1s, "1S"), \
                    (individual_axe_3s, "3S"), \
                    (individual_axe_5s, "5S")]:

                # plot_latency_grouped_by_time(
                #     axe, "latency - write - " + containerID[:8] + " - " + freq, "write", freq, write[write.containerID == containerID][["dt","write"]])
                # plot_latency_grouped_by_time(
                #     axe, "latency - read - " + containerID[:8] + " - " + freq, "read", freq, read[read.containerID == containerID][["dt","read"]])
                plot_latency_grouped_by_time(
                    axe, "latency - sum  - " + containerID[:8] + " - " + freq, "sum", freq, sum[sum.containerID == containerID][["dt","sum"]])
                axe.set_ylabel("Group by " + freq)
                axe.legend()
                if LATENCY_UPPER_LIMIT > 0:
                    axe.set_ylim(1000, LATENCY_UPPER_LIMIT)

            axe = individual_axe_debit
            plot_latency(axe, "debit - " + containerID[:8] , "ops", operations[operations.containerID == containerID])

        ## make graph show only relevant parts of the Experiment
        ## (without big white spaces in the begging and end)
        # start = comulative_sum["dt"].iloc[0].total_seconds()
        # end = comulative_sum["dt"].iloc[-1].total_seconds()
        # start = max(0, start - 10)
        # end = end + 10
        # for axe in [axe_1s, axe_3s, axe_5s, axe_10s]:
        #     ax.set_xlim(start, end)


    #### Print Stats

    process_service_stats_plot(
        df, cassandra_ids, axe_cassandra_cpu, axe_cassandra_bandwidth)
    for index, container_id in enumerate(cassandra_ids):
        process_container_stats_plot(df, container_id, fourth_axes[index])
    #### Plot instances varian

    for service_ids, label, linestyle in [(cassandra_ids, "CASSANDRA", "dashed") \
                                    # ,(ycsbal_ids, "ycsb A Load") \
                                    ,(ycsbar_ids, "YCSB", "solid") \
                                    # ,(ycsbbr_ids, "ycsb B Run") \
                                    # ,(setup_service_ids, "setup service") \
                                    ]:
            # process_service_instances_plot(df, service_ids, axe)
            # process_service_instances_plot(df, service_ids, axe_instances, label)
            process_service_instances_plot(df, service_ids, axe_cassandra_instances, label, linestyle)
    axe_cassandra_instances.legend()

    # per-node resource stats
    process_node_plot(df, axe_nodes)

    process_marks_plot(df, axes)
    return all_figs
    # return [first_fig]
    # return [second_fig]


def print_coloured(msg):
    print(colored(" " + str(msg) + " ", 'green', 'on_blue', attrs=['bold']))


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: {} LOG_FILE OUT_FILE LATENCY_UPPER_LIMIT [TITLE]".format(sys.argv[0]))
    else:
        log_file = sys.argv[1]
        out_file = sys.argv[2]
        title = out_file

        if len(sys.argv) > 3:
            LATENCY_UPPER_LIMIT = int(sys.argv[3])
        else:
            LATENCY_UPPER_LIMIT = -1

        if type(title) == bytes:
            title = str(title, 'utf-8')

        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')

        print_coloured("now loading")
        load_info = load(log_file)

        print_coloured("now processing")
        figs = process(load_info, title)

        # plt.show()
        # # print("creting plot")
        # figs = plot(*data, title)
        print_coloured("saving file")

        pp = PdfPages(out_file + ".pdf")
        for fig in figs:
            # one in each page
            pp.savefig(fig, orientation='landscape')

        # for fig in figs:
        #     # one in each page
        #     plt.show(fig)

        pp.close()
