#!/usr/bin/env python
import json
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from IPython.core.display import Math
from matplotlib.backends.backend_pdf import PdfPages
import pprint
import inspect
import re
from datetime import timedelta
from termcolor import colored

debug_print_logs = False
parse_latency_data = False
x_upper_limit = 4300
# x_upper_limit = 1000


LATENCY_UPPER_LIMIT = 10000
# uncomment  to unset option
# LATENCY_UPPER_LIMIT = -1

pp = pprint.PrettyPrinter(indent=4)

# "[Operation], time_as_ms_since_start, #operations/interval"
START_OVERALL_LINE = re.compile("^\[OVERALL\]\,\sRunTime\(ms\)\,\s(\d+\.*\d*)$")
# [READ], 1000, 1922.5124555160141
READ_STATUS_LINE = re.compile("^\[READ\]\,\s(\d+)\,\s(\d+\.\d+)$")
# "[UPDATE], 0, 3096.2569832402237"
UPDATE_STATUS_LINE = re.compile("^\[UPDATE\]\,\s(\d+)\,\s(\d+\.\d+)$")
# " has finished"
END_STATUS_LINE = re.compile("^\shas\sfinished$")
# "2019-05-31 13:17:06:245 1440 sec: 23863825 operations; 16202.6 current ops/sec; est completion in 9  minutes [READ AverageLatency(us)=782.17] [UPDATE AverageLatency(us)=444.25]"
STATUS_EVERY_10_LINE = re.compile(".*\d+\:\d+\:\d+\:\d+\s(\d+)\ssec\:\s(\d+)\soperations\;\s(\d+\.\d+)\scurrent.*\[READ\sAverageLatency\(us\)\=.*$")

STATUS_EVERY_SECOND =           re.compile(".*\s(\d+)\ssec\:\s(\d+)\soperations\;\s(\d+)\scurrent\s.*$")
STATUS_EVERY_SECOND_VERSION_2 = re.compile(".*\s(\d+)\ssec\:\s(\d+)\soperations\;\s(\d+\.\d+)\scurrent\s.*$")
 # 2 sec: 717 operations; 717 current ops/sec; [READ AverageLatency(us)=9703.14] [UPDATE AverageLatency(us)=10593.02]


# Status Line
# STATUS_EVERY_10_LINE = re.compile("(\d+)\ssec\:\s(\d+)\soperations")
# 2019-05-31 13:16:16:245 1390 sec: 23051290 operations; 16524.2 current ops/sec; est completion in 10 minutes [READ AverageLatency(us)=761.33] [UPDATE AverageLatency(us)=440.51


class Point:
    def sort_function(self):
        return self.x

    def __init__(self, x, y, denomination, containerID):
        self.x = x
        self.y = y
        self.series = denomination
        self.containerID = containerID
    def print(self):
        return "{" +\
            "\"x\":" + str(self.x) + "," +\
            "\"y\":" + str(self.y) + "," +\
            "\"series\":" + str(self.series) + "," +\
            "\"id\":" + "\"" + str(self.containerID) + "\"" +\
            "}"


class ListOfPoints:
    def __init__(self):
        self.list = []

    def add_point(self, point):
        self.list += [point]

    def print(self):
        to_return = "["

        for point in self.list:
            to_return += point.print() + ","

        # remove last ,
        to_return = to_return[:-1]
        to_return += "]"
        return to_return

    def sort_list(self):
        self.list.sort(key=Point.sort_function)


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
                        print(msg)
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
    last = df.iloc[-1].time
    print(last)
    # stop = df[df.mark == 'stop'].iloc[-1].time
    stop = last


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

def process_container_stats_plot(df, container_id, net_axe, disk_axe, cpu_axe, mem_axe):
    # Calculate per-instance resource stats

    stats = df[(df.subject == 'STATS') & (df.id == container_id)]
    stats = stats[['dt', 'id', 'cpu', 'mem', 'rx_bytes', 'tx_bytes']]

    # process bandwidth
    diff_sec = stats.dt.dt.total_seconds().diff()

    # deb_stats = stats[['dt', 'id', 'tx_bytes']]
    # deb_stats.loc[deb_stats.id == id, 'tx_bytes'] = deb_stats.tx_bytes.diff()
    # deb_stats.loc[deb_stats.id == id, 'dt'] = deb_stats.dt.dt.total_seconds().diff()
    # deb_stats.loc[deb_stats.id == id, 'divi'] = deb_stats.tx_bytes / diff_sec
    # print(deb_stats)

    stats["time_diff"] = stats.dt.dt.total_seconds().diff()
    stats["rx_bw"] = stats["rx_bytes"].diff().divide(stats["time_diff"])
    stats["tx_bw"] = stats["tx_bytes"].diff().divide(stats["time_diff"])

    # diff_sec = stats.dt.dt.total_seconds().diff()
    # stats.loc[stats.id == id, 'rx_bw'] = stats.rx_bytes.diff() / diff_sec
    # stats.loc[stats.id == id, 'tx_bw'] = stats.tx_bytes.diff() / diff_sec

    # stats.loc[stats.id == id, 'rx_bw'] = stats.rx_bytes.diff() / stats.time_diff
    # stats.loc[stats.id == id, 'tx_bw'] = stats.tx_bytes.diff() / stats.time_diff

    # print(stats)
    # print(diff_sec)

    stats.set_index("dt")
    dt = stats.dt.dt.total_seconds()

    # name = 'Manager Node'
    cpu_axe.plot(dt, stats.cpu * 100, label="CPU - " + container_id[:8] )
    net_axe.plot(dt, stats.rx_bw / 1024 / 1024, label="Received -" + container_id[:8])
    net_axe.plot(dt, stats.tx_bw / 1024 / 1024, label="Sent - " + container_id[:8])
    mem_axe.plot(dt, stats.mem * 100, label="MEM - " + container_id[:8])

    net_axe.legend()
    disk_axe.legend()
    cpu_axe.legend()
    mem_axe.legend()



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


def create_list_reads_and_writes(logs, containerID, list_of_points):
    started = False
    ended = True
    logs = logs[(logs.subject == 'LOG') & (logs.id == containerID)]
    logs = logs[['dt', 'log', 'service']]
    # as_list_service = list(logs['service'])
    as_list = list(logs['dt'])


    start_time = 0

    for index, line in enumerate(logs['log']):
        # print(line)
        if START_OVERALL_LINE.match(line):
            print("Start!!")
            started = True
            splitted = re.split(START_OVERALL_LINE, line)
            start_time = as_list[index] - timedelta(milliseconds=round(float(splitted[1])))

        if READ_STATUS_LINE.match(line):
            splitted = re.split(READ_STATUS_LINE, line)

            time_of_point = start_time + timedelta(milliseconds=int(splitted[1]))
            simple_point = Point(time_of_point.seconds, round(float(splitted[2])), "\"Lat-Read\"", containerID)
            # list_of_points.add_point(simple_point)

        if UPDATE_STATUS_LINE.match(line):
            splitted = re.split(UPDATE_STATUS_LINE, line)
            time_of_point = start_time + timedelta(milliseconds=int(splitted[1]))
            simple_point = Point(time_of_point.seconds, round(float(splitted[2])), "\"Lat-Write\"", containerID)
            # list_of_points.add_point(simple_point)

        if STATUS_EVERY_10_LINE.match(line):
            print("Mathc the CASSANDRA way")
            status_moment = as_list[index]
            splitted = re.split(STATUS_EVERY_10_LINE, line)
            # current_ops = float(splitted[3])
            simple_point = Point(status_moment.seconds, round(float(splitted[3])), "\"Operations\"", containerID)
            list_of_points.add_point(simple_point)

        if STATUS_EVERY_SECOND.match(line):

            status_moment = as_list[index]
            splitted = re.split(STATUS_EVERY_SECOND, line)
            # current_ops = float(splitted[3])
            simple_point = Point(status_moment.seconds, round(float(splitted[3])), "\"Operations\"", containerID)
            list_of_points.add_point(simple_point)
        if STATUS_EVERY_SECOND_VERSION_2.match(line):

            status_moment = as_list[index]
            splitted = re.split(STATUS_EVERY_SECOND_VERSION_2, line)
            # current_ops = float(splitted[3])
            simple_point = Point(status_moment.seconds, round(float(splitted[3])), "\"Operations\"", containerID)
            list_of_points.add_point(simple_point)

    return list_of_points


def process(df, title=None):
    print(" Services in Experiment: " + str(df.service.unique()))

    # create PDF first page
    first_fig, first_axes = plt.subplots(
        nrows=4, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    axe_instances, axe_host_stats, _, _ = first_axes
    # axe_cassandra_instances, axe_cassandra_cpu, axe_cassandra_bandwidth, axe_nodes =

    # create PDF second page - Both Clients mean
    second_fig, second_axes = plt.subplots(
        nrows=4, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    server_1_net, server_1_disk, server_1_cpu, server_1_mem = second_axes

    # create PDF third page - Only Clients Separated
    third_fig, third_axes = plt.subplots(
        nrows=4, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    server_2_net, server_2_disk, server_2_cpu, server_2_mem = third_axes

    forth_fig, forth_axes = plt.subplots(
        nrows=4, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    server_3_net, server_3_disk, server_3_cpu, server_3_mem = forth_axes

    fifth_fig, fifth_axes = plt.subplots(
        nrows=4, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    server_4_net, server_4_disk, server_4_cpu, server_4_mem = fifth_axes

    sixth_fig, sixth_axes = plt.subplots(
        nrows=4, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    ycsb_load_net, ycsb_load_disk, ycsb_load_cpu, ycsb_load_mem = sixth_axes

    seventh_fig, seventh_axes = plt.subplots(
        nrows=4, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    ycsb_run_net, ycsb_run_disk, ycsb_run_cpu, ycsb_run_mem = seventh_axes



    # cassandra_ids = set(df[df.service == 'cassandra'].id.unique())
    #
    # # create PDF forth page - Stats for cassandra containers
    # fourth_fig, fourth_axes = plt.subplots(
    #     nrows=len(cassandra_ids), ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    # # create PDF forth page - Stats for cassandra containers
    # fifth_fig, fifth_axes = plt.subplots(
    #     nrows=1, ncols=1, sharex=True, figsize=(10, 12), dpi=300)
    # # create PDF forth page - Stats for cassandra containers
    # sixth_fig, sixth_axes = plt.subplots(
    #     nrows=1, ncols=1, sharex=True, figsize=(10, 12), dpi=300)

    # print(sixth_axes)
    # print(fifth_axes)
    # a, b = fifth_axes
    # print(a)
    # print(b)

    # axe_cassandra_instances = sixth_axes
    both_axe_debit = fifth_axes
    # _, axe_cassandra_instances = sixth_axes

    for service_name, group_axe in [("server 1", second_axes), \
                                    ("server 2", third_axes), \
                                    ("server 3", forth_axes), \
                                    ("server 4", fifth_axes), \
                                    ("ycsb load", sixth_axes), \
                                    ("ycsb run", seventh_axes)]:
        group_axe[0].set_title(service_name+r" NET usage [\%]")
        group_axe[1].set_title(service_name+r" DISK usage [\%]")
        group_axe[2].set_title(service_name+r" CPU usage [\%]")
        group_axe[3].set_title(service_name+r" MEM usage [\%]")


    # axe_ycsbal_instances.set_title(
    #     r"Number of " + "work A - Load" + " instances")
    # axe_ycsbar_instances.set_title(
    #     r"Number of " + "work A - Run" + " instances")
    # axe_ycsbbr_instances.set_title(
    #     r"Number of " + "work B - Run" + " instances")
    # axe_setup.set_title(r"Number of " + "axe setup" + " instances")

    axes = concatenate_all_axes(first_axes, second_axes, third_axes, forth_axes, fifth_axes, sixth_axes, seventh_axes)
    all_figs = concatenate_all_figs(first_fig, second_fig, third_fig, forth_fig, fifth_fig, sixth_fig, seventh_fig)
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

    # axe_cassandra_instances.set_ylabel("Número Contentores")
    # both_axe_debit.set_ylabel("Número Operações")
    # sixth_fig.subplots_adjust(top=.90, bottom=.75)
    # fifth_fig.subplots_adjust(top=.90, bottom=.75)


    # axe_reads.set_ylim(bottom=0, top=6000)
    # axe_reads.set_xlim(auto=True)

    # print(type(df))
    server_1_ids = set(df[df.service == 'server-1'].id.unique())
    server_2_ids = set(df[df.service == 'server-2'].id.unique())
    server_3_ids = set(df[df.service == 'server-3'].id.unique())
    server_4_ids = set(df[df.service == 'server-4'].id.unique())
    ycsb_client_load_ids = set(df[df.service == 'ycsb-client-load'].id.unique())
    ycsb_client_run_ids = set(df[df.service == 'ycsb-client-run'].id.unique())
    # ycsb_client_run_ids = set(df[df.service == 'ycsbar'].id.unique())

    list_of_points = ListOfPoints()
    for id in ycsb_client_run_ids :
        print(id)
        list_of_points = create_list_reads_and_writes(df, id, list_of_points)

    list_of_points.sort_list()
    json_info = list_of_points.print()
    with open("ycsb_output.json", "w") as text_file:
        text_file.write(json_info)


    #### Print Stats
    # server_ids = list(server_1_ids) + list(server_4_ids) + list(server_3_ids) + list(server_2_ids)
    # server_ids = ycsb_client_load_ids
    # process_service_stats_plot(df, server_ids, axe_cassandra_cpu, axe_cassandra_bandwidth)
    #
    for service_ids, group_axes in [(server_1_ids,  second_axes), \
                              (server_2_ids, third_axes), \
                              (server_3_ids, forth_axes), \
                              (server_4_ids, fifth_axes), \
                              (ycsb_client_load_ids, sixth_axes), \
                              (ycsb_client_run_ids, seventh_axes),
        ]:
        for container_id in service_ids:
            process_container_stats_plot(df, container_id, \
                                            net_axe= group_axes[0], \
                                            disk_axe= group_axes[1], \
                                            cpu_axe= group_axes[2], \
                                            mem_axe=group_axes[3])
    for service_name, service_ids in [("server 1", server_1_ids), \
                                    ("server 2", server_2_ids), \
                                    ("server 3", server_3_ids), \
                                    ("server 4", server_4_ids), \
                                    ("ycsb load", ycsb_client_load_ids), \
                                    ("ycsb run", ycsb_client_run_ids)]:

        process_service_instances_plot(df, service_ids, axe_instances, label=service_name)

    # for service_ids in [server_1_ids, server_2_ids, server_3_ids, server_4_ids, ycsb_client_load_ids]
    #     for index, container_id in enumerate(service_ids):
    #         process_container_stats_plot(df, container_id, fourth_axes[index])
    # #### Plot instances varian
    #
    # for service_ids, label, linestyle in [(cassandra_ids, "CASSANDRA", "dashed") \
    #                                 # ,(ycsbal_ids, "ycsb A Load") \
    #                                 ,(ycsbar_ids, "YCSB", "solid") \
    #                                 # ,(ycsbbr_ids, "ycsb B Run") \
    #                                 # ,(setup_service_ids, "setup service") \
    #                                 ]:
    #         # process_service_instances_plot(df, service_ids, axe)
    #         # process_service_instances_plot(df, service_ids, axe_instances, label)
    #         process_service_instances_plot(df, service_ids, axe_cassandra_instances, label, linestyle)
    # axe_cassandra_instances.legend()

    # per-node resource stats
    process_node_plot(df, axe_host_stats)

    process_marks_plot(df, axes)
    return all_figs



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
