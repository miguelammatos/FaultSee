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

                print(split)
                print(" ", "time:", time)
                print(" ", "id:", id)
                print(" ", "msg:", msg)
                print(" ", "subject:", subject)

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
    print(df.time)
    df.time = pd.to_datetime(df.time)
    df = df.sort_values(by='time')

    start = df[df.mark == 'start'].iloc[0].time
    stop = df[df.mark == 'stop'].iloc[-1].time

    df = df[(df.time >= start) & (df.time <= stop)]
    df['dt'] = df.time - df.time.min()

    return df


def process(df):
    # find nginx & siege instances
    nginx = set(df[df.service == 'nginx'].id.unique())
    siege = set(df[df.service == 'siege'].id.unique())

    # compute requests/s for each nginx instance
    requests = pd.DataFrame()
    for id in nginx:
        r = df[(df.subject == 'LOG') & (df.id == id)][['dt']]
        r['requests'] = 1
        r = r.set_index('dt')
        r = r.groupby(pd.Grouper(freq='1S')).sum()
        r['id'] = id

        requests = requests.append(r)

    requests = requests.sort_index()
    requests['dt'] = requests.index
    requests = requests[['dt', 'id', 'requests']]

    # per-instance resource stats
    stats = df[(df.subject == 'STATS') & df.id.isin(nginx)]
    stats = stats[['dt', 'id', 'cpu', 'mem', 'rx_bytes', 'tx_bytes']]

    # compute bytes/s for each nginx instance
    for id in nginx:
        s = stats[stats.id == id]
        dt = s.dt.dt.total_seconds().diff()
        stats.loc[stats.id == id, 'rx_bw'] = s.rx_bytes.diff() / dt
        stats.loc[stats.id == id, 'tx_bw'] = s.tx_bytes.diff() / dt

    requests = requests.sort_index()
    requests['dt'] = requests.index
    requests = requests[['dt', 'id', 'requests']]

    # per-node resource stats
    nodes = df[df.subject == 'HOST']
    nodes = nodes[['dt', 'id', 'cpu', 'mem']]

    # compute up/down events for siege service
    events = df[df.id.isin(siege) & df.status.isin(['start', 'kill'])].copy()
    events.status = ((events.status == 'start').astype('int')
                     - (events.status == 'kill').astype('int'))
    events['instances'] = events.status.cumsum()
    events['i'] = 0
    for i, id in enumerate(events.id.unique()):
        events.loc[events.id == id, 'i'] = i + 1

    events = events[['dt', 'id', 'i', 'status', 'instances']]

    # start/stop/churn marks
    marks = df[df.subject == 'MARK']
    # only keep marks of one node, they're all the same anyway
    marks = marks[marks.id == marks.id[0]]
    marks = marks[marks.mark == 'churn']
    # marks = marks[['dt', 'mark', 'service', 'churn']]

    return requests, stats, nodes, events, marks


def plot(requests, stats, nodes, events, marks, title=None):
    fig, axes = plt.subplots(
        nrows=5, ncols=1, sharex=True,
        figsize=(10, 12), dpi=300)

    ax_instances, ax_req, ax_cpu, ax_bw, ax_nodes = axes

    ax_instances.set_title(r"Number of siege instances")
    ax_req.set_title(r"Served request rate [req/s]")
    ax_cpu.set_title(r"nginx CPU usage [\%]")
    ax_bw.set_title(r"nginx bandwidth usage [MiB/s]")
    ax_nodes.set_title(r"Node CPU and memory usage [\%]")

    for ax in axes:
        ax.yaxis.grid()
        ax.set_xlim(0, nodes.dt.dt.total_seconds().max())

    for _, mark in marks.iterrows():
        if mark.service != 'siege':
            continue
        for ax in axes:
            ax.axvline(mark['dt'].total_seconds(),
                       color=(0, 0, 0, .1), ls='--')

    instances = events.set_index('dt')
    instances = instances.resample('S').last().ffill()
    instances['dt'] = instances.index
    ax_instances.plot(instances.dt.dt.total_seconds(), instances.instances)

    for id in stats.id.unique():
        st = stats[stats.id == id]
        rq = requests[requests.id == id]
        ax_req.plot(rq.dt.dt.total_seconds(), rq.requests)
        dt = st.dt.dt.total_seconds()
        ax_cpu.plot(dt, st.cpu * 100)
        ax_bw.plot(dt, st.rx_bw / 1024 / 1024, label="Received", ls=':')
        ax_bw.plot(dt, st.tx_bw / 1024 / 1024, label="Transmitted")

    colors = matplotlib.rcParams['axes.prop_cycle']
    colors = [c['color'] for c in colors]
    manager = list(nodes.id.unique())[0]
    st_manager, st_worker = nodes[nodes.id
                                  == manager], nodes[nodes.id != manager]

    st = st_manager.set_index('dt')
    st = st.groupby(pd.Grouper(freq='5S')).mean()
    st['dt'] = st.index
    dt = st.dt.dt.total_seconds()
    name = 'Manager Node'
    ax_nodes.plot(dt, st.cpu * 100, label=name + " CPU", lw=2)
    ax_nodes.plot(dt, st.mem * 100, label=name + " MEM", lw=3, ls=':')

    st = st_worker.set_index('dt')
    st = st.groupby(pd.Grouper(freq='5S')).mean()
    st['dt'] = st.index
    dt = st.dt.dt.total_seconds()
    name = 'Workers Average'
    ax_nodes.plot(dt, st.cpu * 100, label=name + " CPU", lw=1)
    ax_nodes.plot(dt, st.mem * 100, label=name + " MEM", lw=1, ls='--')

    # for (i, id), c in zip(enumerate(nodes.id.unique()), colors):
    #     st = nodes[nodes.id == id]
    #     # smoothen stats
    #     st = st.set_index('dt')
    #     st = st.groupby(pd.Grouper(freq='5S')).mean()
    #     st['dt'] = st.index
    #     dt = st.dt.dt.total_seconds()
    #     name = "node-{}".format(i)
    #     ax_nodes.plot(dt, st.cpu * 100, label=name + " CPU", c=c)
    #     ax_nodes.plot(dt, st.mem * 100, label=name + " MEM", c=c, ls=':')

    ax_instances.set_ylim(bottom=0)
    ax_req.set_ylim(bottom=0)
    ax_cpu.set_ylim(bottom=0)
    ax_bw.set_ylim(bottom=0)
    ax_nodes.set_ylim(bottom=0)

    ax_bw.legend()
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

        print("now processing")
        data = process(load(log_file))
        print("creting plot")
        fig = plot(*data, title)
        print("saving file")
        fig.savefig(out_file + ".pdf")
