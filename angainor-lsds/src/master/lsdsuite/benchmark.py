import logging
import time
import json
import traceback
from os.path import join

from .churn import Churn

log = logging.getLogger(__name__)

# Was previously a field in config.yaml, does this need to be configurable?
# If running as container, it is difficult to support writing to an arbitrary
# location (except if we mount the whole host filesystem into the container,
# but this is obviously overkill).
RESULTS_DIR = "./results"
COMPRESS_LOGS = False


class Benchmark(object):
    def __init__(self, engine, config, name, spec, churn=None,
                 churn_string=None, run_time=None, start_time=0, end_time=0):
        from datetime import datetime
        self.date = datetime.now().replace(microsecond=0)

        self.engine = engine
        self.nodes = config['nodes']
        self.lsds_dir = config['lsds_dir']
        self.name = name
        self.spec = spec
        self.config = config

        if not churn and not run_time:
            raise ValueError("Either churn or run_time must be specified!")

        if churn:
            churn = Churn(churn)
            faults_folder_in_host = self.config["faults_folder_host"]
            faults_folder_in_container = self.config["faults_folder_container"]
            self._inject_faults_volumes(spec, faults_folder_in_host, faults_folder_in_container)
            self._inject_none_restart_policy(spec)
            answer_list = self.engine.parallel_send_command("churn_string", **{"churn_string": churn_string})
            # check all answers?
            for status, msg in answer_list:
                if status != 'ok':
                    raise ValueError("Parsing Experiment Events Failed.. ", msg)
            self.start_time = 0
        else:
            self.start_time = start_time

        self.churn = churn
        self.run_time = run_time
        self.end_time = end_time

        self.app = None
        self.run = 0

    @property
    def log_file(self):
        return ("{date}--{name}--run-{run}.log"
                .format(date=self.date.isoformat(),
                        name=self.name,
                        run=self.run))

    @property
    def results_dir(self):
        from os.path import join
        return join("{date}--{name}".format(date=self.date.isoformat(),
                                            name=self.name),
                    "run-{run}".format(run=self.run))

    @property
    def mark(self):
        return {
            "type": "benchmark",
            "name": self.name,
            "run": self.run
        }

    def start(self, dry_run=False):
        """Runs one run of the benchmark."""
        if self.app is not None:
            log.info("%s already started", self)
            return

        self.run += 1
        log.info("%s: starting run %d", self, self.run)
        # TODO: make this more engine-agnostic
        # maybe move it to engine.create_app
        self.engine.send('log', file=self.log_file)

        msg = dict(self.mark, status="start")
        self.engine.send('mark', msg=json.dumps(msg))

        spec = self.spec
        if self.churn:
            self.churn.apply_start(spec)

        self.app = self.engine.create_app(self.name, spec)
        try:
            if self.churn:
                log.info("%s: starting churn", self)
                self.churn.start(self.engine, self.app, dry_run, 10)
            else:
                log.info("%s: waiting %ds before start", self, self.start_time)
                time.sleep(self.start_time)

                log.info("%s: running for %ds", self, self.run_time)
                time.sleep(self.run_time)

            log.info("%s: waiting %ds before end", self, self.end_time)
            time.sleep(self.end_time)
        except:
            traceback.print_exc()
            log.warning("There was an ERROR, aborting!", exc_info=1)

        self.stop()

    def stop(self, wait=30, get_logs=True):
        if self.app is None:
            return

        self.app.remove()
        log.info("%s: waiting %ds for services to shut down", self, wait)
        time.sleep(wait)
        self.app = None

        msg = dict(self.mark, status="stop")
        self.engine.send('mark', msg=json.dumps(msg))
        self.engine.send('log', file=None)

        log.info("%s: end of run %d", self, self.run)

        if get_logs:
            self.get_logs()

        if self.churn:
            path = RESULTS_DIR  # abspath(RESULTS_DIR)
            experiment_results_folder = join(path, self.results_dir)

            self.churn.stop(self.engine, experiment_results_folder)

    def manual_get_logs(self, local_folder, remote_file_name):
        import gzip
        from os import makedirs
        from os.path import abspath, join
        from shutil import copyfileobj
        from glob import iglob
        from subprocess import run

        log.info("%s: fetching logs", self)
        for i, node in enumerate(self.nodes):
            local_path = local_folder
            makedirs(local_path, exist_ok=True)
            output_path = join(local_path, "{i}.log".format(i=i))

            self._get_logs_ssh(node, output_path, remote_file_name)
        out = join(local_path, "out.log")

        run(["sort", "-o", out, "-m", *iglob("*.log")], check=True)
        log.info("%s: logs saved to %s", self, out)

    def get_logs(self):
        from os.path import join
        from glob import iglob
        from subprocess import run

        log.info("%s: fetching logs", self)
        for i, node in enumerate(self.nodes):
            self._get_logs(node, i)

        # merge
        path = RESULTS_DIR  # abspath(RESULTS_DIR)
        path = join(path, self.results_dir)

        out = join(path, "out.log")
        pat = join(path, "nodes", "*.log")

        run(["sort", "-o", out, "-m", *iglob(pat)], check=True)
        log.info("%s: logs saved to %s", self, out)

    def _inject_faults_volumes(self, spec, faults_folder_in_host, faults_folder_in_container):
        services = spec.get('services')
        if not services:
            log.warning("No services specified in spec.")
            return

        for name, service in services.items():
            log.debug("Injecting Faults Volume in {name}: ".format(
                name=name), service)
            self.engine.inject_faults_volumes(service, faults_folder_in_host, faults_folder_in_container)

    # this method makes sure containers do not restart when killed
    def _inject_none_restart_policy(self, spec):
        services = spec.get('services')
        if not services:
            log.warning("No services specified in spec.")
            return

        for name, service in services.items():
            log.debug("Making restart policy None for service [name]".format(name=name))
            self.engine.make_restart_policy_none(service)

    def _get_logs(self, node, i):
        import gzip
        from os import makedirs
        from os.path import abspath, join
        from shutil import copyfileobj

        remote_path = abspath(self.lsds_dir)
        remote_path = join(remote_path, "logs", self.log_file)

        local_path = RESULTS_DIR  # abspath(RESULTS_DIR)
        local_path = join(local_path, self.results_dir, "nodes")
        makedirs(local_path, exist_ok=True)
        output_path = join(local_path, "{i}.log".format(i=i))

        if COMPRESS_LOGS:
            local_path = join(local_path, "{i}.log.gz".format(i=i))
        else:
            local_path = output_path

        log.debug("%s: node %d: fetching logs from %s to %s",
                  self, i, remote_path, local_path)

        if i == 0 and not node.get('remote'):
            self._get_logs_local(node, local_path, remote_path)
        else:
            self._get_logs_ssh(node, local_path, remote_path)

        if COMPRESS_LOGS:
            with open(output_path, 'wb') as f:
                with gzip.open(local_path, 'rb') as g:
                    copyfileobj(g, f)

    def _get_logs_local(self, node, local_path, remote_path):
        from shutil import copy
        copy(remote_path, local_path)

    def _get_logs_ssh(self, node, local_path, remote_path):
        from . import get_ssh

        def progress(i, total):
            # show update every 10%
            current = int(10 * i/total) * 10
            if current != progress.cnt:
                progress.cnt = current
                log.debug("%s: SSH progress: %3.0f%%", self, 100 * i/total)
        progress.cnt = -1
        with get_ssh(node) as ssh:
            sftp = ssh.open_sftp()
            sftp.get(remote_path, local_path, callback=progress)

    def __repr__(self):
        return "Benchmark[{name}]".format(name=self.name)

