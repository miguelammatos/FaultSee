import json
from os.path import join

import pandas
import logging

log = logging.getLogger(__name__)


class Parser(object):
    def __init__(self, filename):
        self.filename = filename
        self.logs = []
        self.marks = []
        self.individual_container_stats = []
        self.events = []
        self.containers_ids = []
        self.host_stats = []

    def process_file(self, directory_path):
        log.info("Loading " + str(self.filename))
        self._load(self.filename)

        log.info("Sorting data")
        self._sort_by_time()

        log.info("Create containers identification info")
        self._create_containers_ids()
        log.info("Process containers stats")
        self._process_container_stats()
        log.info("Process hosts stats")
        self._process_host_stats()
        log.info("Writing to files")
        self._write_to_files(directory_path)

    # this trnasforms dates into amount of seconds since beginning of experiment
    def _process_relative_time(self, min_time):
        for array in [self.logs, self.marks, self.individual_container_stats, self.events, self.host_stats]:
            for entry in array:
                time = entry["time"]
                entry["time"] = (time - min_time).total_seconds()

    def _sort_by_time(self):
        pairs = [
            self.logs,
            self.marks,
            self.individual_container_stats,
            self.events,
            self.host_stats,
        ]

        def get_time(val):
            return val.get("time")

        for array in pairs:
            array.sort(key=get_time)

    def _write_to_files(self, directory_path):
        pairs = [
            ("containers_logs", self.logs),
            ("marks", self.marks),
            ("containers_stats", self.individual_container_stats),
            ("containers_events", self.events),
            ("host_stats", self.host_stats),
            ("containers_ids", self.containers_ids),
        ]
        log.info("Writing to files in directory: " + str(directory_path))

        for filename, array in pairs:
            file_path = join(directory_path, filename + ".json")
            log.info("Writing to file " + str(file_path))
            self._dump_json_to_file(file_path, array)

    def _load(self, path):
        min_time = None
        with open(path) as f:
            for line in f:
                # try:
                    line = line.strip()
                    split = line.split('\t', 2)
                    while len(split) < 3:
                        split.append("")
                    time, id, msg = split
                    time, subject = time.split(' ', 1)
                    time = pandas.to_datetime(time)
                    if min_time is None or time < min_time:
                        min_time = time

                    subject = subject[1:-1]  # removes brackets

                    if subject == 'LOG':
                        container_id = id
                        self._parse_log_msg(time, container_id, msg)

                    if subject == 'EVENT':
                        event = json.loads(msg)
                        if event['Type'] != 'container':
                            # only interested in container events
                            continue
                        self._parse_container_event(time, id, event)

                    if subject == 'STATS':
                        stats = json.loads(msg)
                        container_id = id
                        self._parse_individual_container_stats(time, container_id, stats)

                    if subject == 'HOST':
                        hostname = id
                        host_stats = json.loads(msg)
                        self._parse_host_stats(time, hostname, host_stats)

                    if subject == 'MARK':
                        mark = json.loads(msg)
                        hostname = id
                        self._parse_mark(time, hostname, mark)

                # except Exception as e:
                #     log.error("Could not parse line: " + str(line))
                #     log.error(e)
        self._process_relative_time(min_time)

    def _parse_container_event(self, time, container_id, event):
        if event["Action"] not in ["start", "die"]:
            # ignore
            return

        attr = event['Actor']['Attributes']
        service = attr.get('com.docker.swarm.service.name')

        slot_number = attr.get("com.docker.swarm.task.name").split(".")[1]
        action = event["Action"]
        processed_container_event = dict(time=time, container_id=container_id, service=service, slot=slot_number,
                                         action=action)
        self.events.append(processed_container_event)

    def _create_containers_ids(self):
        container_ids = {}

        for event in self.events:
            cont_id = event["container_id"]
            service = event["service"]
            slot = event["slot"]

            container_ids[cont_id] = {"container_id": cont_id, "service": service, "slot": slot}
        self.containers_ids = []
        for _, value in container_ids.items():
            self.containers_ids.append(value)

    def _get_container_ids(self):
        return_list = []
        for container in self.containers_ids:
            return_list.append(container["container_id"])

        return return_list

    def _get_nodes_hostname(self):
        hostname_dict = {}
        for entry in self.host_stats:
            hostname = entry["hostname"]
            key_exists = hostname_dict.get(hostname, None)
            if key_exists is None:
                hostname_dict[hostname] = True

        return hostname_dict.keys()

    def _parse_log_msg(self, time, container_id, msg):
        processed_log = dict(time=time, container_id=container_id, msg=msg)
        self.logs.append(processed_log)

    def _parse_mark(self, time, hostname, mark):
        mark_type = mark.get("type", None)

        if mark_type is None:
            # log.debug(str(hostname) + " Mark does not have TYPE : " + str(mark))
            mark_msg = mark

        elif mark_type == "benchmark":
            # log.debug(str(hostname) + " Mark benchmark: " + str(mark))
            mark_msg = mark['status']

        elif mark_type == "churn":
            # log.debug(str(hostname) + " Mark churn: " + str(mark))
            mark_msg = mark["op"]

        elif mark_type == "operation":
            # log.debug(str(hostname) + " Mark Operation: " + str(mark))
            mark_msg = mark["operation"]
        elif mark_type == "event":
            # log.debug(str(hostname) + " Mark event: " + str(mark))
            mark_msg = mark["moment"]

        else:
            log.debug("Unsupported mark type: " + str(mark))
            mark_msg = mark

        processed_mark = dict(time=time, hostname=hostname, msg=mark_msg)
        self.marks.append(processed_mark)

    def _parse_individual_container_stats(self, time, container_id, stats):
        # print(stats["networks"])

        preread = stats['preread']
        if preread.startswith("0001"):
            cpu = 0
        else:
            timedelta = (pandas.to_datetime(stats['read']) - pandas.to_datetime(preread)).to_timedelta64()
            timedelta = timedelta.astype('int')

            cpu = (stats['cpu_stats']['cpu_usage']['total_usage']
                   - stats['precpu_stats']['cpu_usage']['total_usage'])
            # n=len(msg['cpu_stats']['cpu_usage']['percpu_usage'])
            cpu /= timedelta

        # incoming
        rx_bytes = 0
        rx_packets = 0  # number
        rx_dropped = 0  # number
        # outgoing
        tx_bytes = 0
        tx_packets = 0  # number
        tx_dropped = 0  # number
        # data.update(msg['networks']['eth0'])
        for network, netStats in stats["networks"].items():
            rx_bytes += netStats["rx_bytes"]
            rx_packets += netStats["rx_packets"]
            rx_dropped += netStats["rx_dropped"]
            tx_bytes += netStats["tx_bytes"]
            tx_packets += netStats["tx_packets"]
            tx_dropped += netStats["tx_dropped"]
        #
        mem = stats['memory_stats']['usage']
        read_and_write_bytes = stats["blkio_stats"]["io_service_bytes_recursive"]

        container_stats = dict(time=time, container_id=container_id,
                               cpu=cpu, mem=mem,
                               # netOut=netOut, netIn=netIn,
                               rx_bytes=rx_bytes,
                               rx_packets=rx_packets,
                               rx_dropped=rx_dropped,
                               tx_bytes=tx_bytes,
                               tx_packets=tx_packets,
                               tx_dropped=tx_dropped,
                               read_and_write_bytes=read_and_write_bytes
                               )

        self.individual_container_stats.append(container_stats)

    def _process_container_stats(self):
        dataframe = pandas.DataFrame(self.individual_container_stats)
        dataframe = dataframe.sort_values(by='time')

        processed_individual = []
        containers_ids = self._get_container_ids()
        for container in containers_ids:
            container_dataframe = dataframe[dataframe.container_id == container]

            container_dataframe = container_dataframe[["time", "container_id", "cpu", "mem", "rx_bytes", "rx_packets", "rx_dropped", "tx_bytes", "tx_packets", "tx_dropped"]]
            # , "read_and_write_byte"

            # CPU alread comes pre processed
            container_dataframe["time_diff"] = container_dataframe.time.diff()
            # process bandwidth
            container_dataframe["rx_bytes"] = container_dataframe["rx_bytes"].diff().divide(container_dataframe["time_diff"])
            container_dataframe["rx_packets"] = container_dataframe["rx_packets"].diff().divide(container_dataframe["time_diff"])
            container_dataframe["rx_dropped"] = container_dataframe["rx_dropped"].diff().divide(container_dataframe["time_diff"])
            container_dataframe["tx_bytes"] = container_dataframe["tx_bytes"].diff().divide(container_dataframe["time_diff"])
            container_dataframe["tx_packets"] = container_dataframe["tx_packets"].diff().divide(container_dataframe["time_diff"])
            container_dataframe["tx_dropped"] = container_dataframe["tx_dropped"].diff().divide(container_dataframe["time_diff"])
            # first one has NaN has values
            container_dataframe = container_dataframe.iloc[1:]

            processed_container_stats = container_dataframe.to_dict('r')
            processed_individual += processed_container_stats

        self.individual_container_stats = processed_individual

    def _parse_host_stats(self, time, hostname, host_stats):

        # gets percent of all combined
        cpu = host_stats['cpuPercent'][0]
        mem = host_stats['mem']['usedPercent']
        netOut = host_stats['net']['all']['bytesSent']
        netIn = host_stats['net']['all']['bytesRecv']

        disk_read = 0
        disk_write = 0
        for interface, content in host_stats['disk'].items():
            disk_read += content['readBytes']
            disk_write += content['writeBytes']

        processed_host_stats = dict(time=time, hostname=hostname, cpu=cpu, mem=mem, netOut=netOut, netIn=netIn,
                                    diskRead=disk_read, diskWrite=disk_write)
        self.host_stats.append(processed_host_stats)

    def _process_host_stats(self):
        dataframe = pandas.DataFrame(self.host_stats)
        dataframe = dataframe.sort_values(by='time')

        processed_individual = []
        nodes_hostname = self._get_nodes_hostname()
        for host in nodes_hostname:
            host_dataframe = dataframe[dataframe.hostname == host]
            host_dataframe = host_dataframe[["time", "hostname", "cpu", "mem", "netOut", "netIn", "diskRead", "diskWrite"]]

            # CPU already comes pre processed
            host_dataframe["time_diff"] = host_dataframe.time.diff()
            # process bandwidth
            host_dataframe["netOut"] = host_dataframe["netOut"].diff().divide(host_dataframe["time_diff"])
            host_dataframe["netIn"] = host_dataframe["netIn"].diff().divide(host_dataframe["time_diff"])
            host_dataframe["diskRead"] = host_dataframe["diskRead"].diff().divide(host_dataframe["time_diff"])
            host_dataframe["diskWrite"] = host_dataframe["diskWrite"].diff().divide(host_dataframe["time_diff"])
            # first one has NaN has values
            host_dataframe = host_dataframe.iloc[1:]
            processed_host_stats = host_dataframe.to_dict('r')
            processed_individual += processed_host_stats

        self.host_stats = processed_individual

    @staticmethod
    def _dump_json_to_file(file_path, array):
        # Get a file object with write permission.
        with open(file_path, 'w') as file_object:
            # Save dict data into the JSON file.
            json.dump(array, file_object)
