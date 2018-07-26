#!/usr/bin/env python
import json
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt


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
                    if msg.startswith("REQ_LATENCY"):
                        data['req_latency'] = int(msg.split(' ')[1]) // 1000 / 1000

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
                        dt = (pd.to_datetime(msg['read']) -
                              pd.to_datetime(preread)).to_timedelta64()
                        dt = dt.astype('int')
                        cpu = (msg['cpu_stats']['cpu_usage']['total_usage'] -
                               msg['precpu_stats']['cpu_usage']['total_usage'])
                        # n=len(msg['cpu_stats']['cpu_usage']['percpu_usage'])
                        cpu /= dt

                    data['cpu'] = cpu
                    data['mem'] = msg['memory_stats']['usage']
                    data.update(msg['networks']['eth0'])

                if subject == 'HOST':
                    msg = json.loads(msg)
                    data['cpu'] = msg['cpuPercent'][0] / 100
                    data['mem'] = msg['mem']['usedPercent'] / 100

                if subject == 'MARK':
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

                yield data

    df = pd.DataFrame(read(path))
    df.time = pd.to_datetime(df.time)
    df = df.sort_values(by='time')

    start = df[df.mark == 'start'].iloc[0].time
    stop = df[df.mark == 'stop'].iloc[-1].time

    df = df[(df.time >= start) & (df.time <= stop)]
    df['dt'] = df.time - df.time.min()

    return df


def process(df):
    # find bft instances
    bft_server = set(df[df.service == 'bft-server'].id.unique())
    bft_client = set(df[df.service == 'bft-client'].id.unique())

    # compute total requests/s
    requests = df[df.req_latency.notnull()][['dt']]
    requests['requests'] = 1
    requests = requests.set_index('dt')
    requests = requests.groupby(pd.Grouper(freq='1S')).sum()

    # compute average latency
    latencies = df[df.req_latency.notnull()][['dt', 'req_latency']]
    latencies = latencies.set_index('dt')
    latencies = latencies.groupby(pd.Grouper(freq='3S')).mean()

    # per-instance resource stats
    stats = df[(df.subject == 'STATS') & df.id.isin(bft_server)]
    stats = stats[['dt', 'id', 'cpu', 'mem', 'rx_bytes', 'tx_bytes']]

    # compute bytes/s for each bft server instance
    for id in bft_server:
        s = stats[stats.id == id]
        dt = s.dt.dt.total_seconds().diff()
        stats.loc[stats.id == id, 'rx_bw'] = s.rx_bytes.diff() / dt
        stats.loc[stats.id == id, 'tx_bw'] = s.tx_bytes.diff() / dt

    # per-node resource stats
    nodes = df[df.subject == 'HOST']
    nodes = nodes[['dt', 'id', 'cpu', 'mem']]

    # compute up/down events for bft client
    # events = df[df.id.isin(bft_client) & df.status.isin(['start', 'die'])].copy()
    # events.status = ((events.status == 'start').astype('int') -
    #                  (events.status == 'die').astype('int'))
    # events['instances'] = events.status.cumsum()
    # events['i'] = 0
    # for i, id in enumerate(events.id.unique()):
    #     events.loc[events.id == id, 'i'] = i + 1
    #
    # events = events[['dt', 'id', 'i', 'status', 'instances']]

    all_status = df[df.status.isin(['start', 'die'])]
    all_events = pd.DataFrame()
    for service_type, service_ids in [
        ('clients', bft_client),  # ('servers', bft_server)
    ]:
        events = all_status[df.id.isin(service_ids)].copy()
        events.status = ((events.status == 'start').astype('int') -
                         (events.status == 'die').astype('int'))
        events['instances'] = events.status.cumsum()
        events['i'] = 0
        for i, id in enumerate(events.id.unique()):
            events.loc[events.id == id, 'i'] = i + 1
        events['service_type'] = service_type

        events = events[['dt', 'id', 'i', 'status', 'instances', 'service_type']]
        all_events = all_events.append(events)

    # start/stop/churn marks
    marks = df[df.subject == 'MARK']
    # only keep marks of one node, they're all the same anyway
    marks = marks[marks.id == marks.id[0]]
    marks = marks[marks.mark == 'churn']
    marks = marks[['dt', 'mark', 'service', 'churn']]

    return requests, latencies, stats, nodes, all_events, marks


def plot(requests, latencies, stats, nodes, events, marks, title=None):
    fig, axes = plt.subplots(
        nrows=6, ncols=1, sharex=True,
        figsize=(10, 12), dpi=300)

    ax_instances, ax_req, ax_lat, ax_cpu, ax_bw, ax_nodes = axes

    ax_instances.set_title(r"Running Bft instances")
    ax_req.set_title(r"Served request rate [req/s]")
    ax_lat.set_title(r"Average response time [ms]")
    ax_cpu.set_title(r"Bft-server CPU usage [\%]")
    ax_bw.set_title(r"Bft-server bandwidth usage [MiB/s]")
    ax_nodes.set_title(r"Node CPU and memory usage [\%]")

    for ax in axes:
        ax.yaxis.grid()
        ax.set_xlim(0, nodes.dt.dt.total_seconds().max())

    for _, mark in marks.iterrows():
        if mark.service != 'bft_server':
            continue
        for ax in axes:
            ax.axvline(mark['dt'].total_seconds(),
                       color=(0, 0, 0, .1), ls='--')

    # instances = events.set_index('dt')
    # instances = instances.resample('S').mean().ffill()
    # instances['dt'] = instances.index
    # ax_instances.plot(instances.dt.dt.total_seconds(), instances.instances)

    for service_type in events.service_type.unique():
        # print(service_type)
        instances = events[events.service_type == service_type]
        instances = instances.set_index('dt')
        instances = instances.resample('S').last().ffill()
        instances['dt'] = instances.index
        ax_instances.plot(
            instances.dt.dt.total_seconds(),
            instances.instances,
            label=service_type
        )

    ax_req.plot(requests.index.total_seconds(), requests.requests)
    ax_lat.set_yscale('log')
    ax_lat.plot(latencies.index.total_seconds(), latencies.req_latency)

    for i, id in enumerate(stats.id.unique()):
        name = "peer-%d" % i
        st = stats[stats.id == id]
        # rq = requests[requests.id == id]
        # ax_req.plot(rq.dt.dt.total_seconds(), rq.requests)
        dt = st.dt.dt.total_seconds()
        ax_cpu.plot(dt, st.cpu * 100, label=name)
        ax_bw.plot(dt, (st.rx_bw + st.tx_bw) / 1024 / 1024, label=name)

    colors = matplotlib.rcParams['axes.prop_cycle']
    colors = [c['color'] for c in colors]
    for (i, id), c in zip(enumerate(nodes.id.unique()), colors):
        st = nodes[nodes.id == id]
        # smoothen stats
        st = st.set_index('dt')
        st = st.groupby(pd.Grouper(freq='5S')).mean()
        st['dt'] = st.index
        dt = st.dt.dt.total_seconds()
        name = "node-{}".format(i)
        ax_nodes.plot(dt, st.cpu * 100, label=name + " CPU", c=c)
        ax_nodes.plot(dt, st.mem * 100, label=name + " MEM", c=c, ls=':')

    ax_instances.set_ylim(bottom=0)
    ax_req.set_ylim(bottom=0)
    ax_cpu.set_ylim(bottom=0)
    ax_bw.set_ylim(bottom=0)
    ax_nodes.set_ylim(bottom=0)

    # Add vertical lines where servers get killed or restarted
    server_marks = marks[
        (marks.service == 'bft-server') &
        (marks.churn.str.startswith('kill', na=False))
    ]
    churn_times = server_marks.dt.dt.total_seconds()
    # for time in churn_times:
    #     for axis in axes:
    #         axis.axvline(time, linestyle='dotted', linewidth=1, color='0', label='test')
    # HACK: Hardcode start and end lines
    start_time, end_time = churn_times
    ax_instances.axvline(
        start_time, linestyle=':', label='1 server killed',
        linewidth=1, color='0',
    )
    ax_instances.axvline(
        end_time, linestyle='--', label='1 server started',
        linewidth=1, color='0'
    )
    for axis in list(axes)[1:]:
        axis.axvline(
            start_time, linestyle=':',
            linewidth=1, color='0',
        )
        axis.axvline(
            end_time, linestyle='--',
            linewidth=1, color='0'
        )

    ax_instances.legend()
    ax_bw.legend()
    ax_cpu.legend()
    ax_nodes.legend()

    ax_nodes.set_xlabel("Time [s]")

    if title:
        fig.suptitle(title, fontsize=20)

    fig.tight_layout()
    fig.subplots_adjust(top=.93, bottom=.07)
    return fig


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: {} LOG_FILE OUT_FILE [TITLE]".format(sys.argv[0]))
    else:
        log_file = sys.argv[1]
        out_file = sys.argv[2]
        if len(sys.argv) > 3:
            title = sys.argv[3]
        else:
            title = out_file

        if type(title) == bytes:
            title = str(title, 'utf-8')

        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')

        data = process(load(log_file))
        fig = plot(*data, title)
        fig.savefig(out_file + ".pdf")
