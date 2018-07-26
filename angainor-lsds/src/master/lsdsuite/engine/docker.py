import re
import logging
import time
import threading
import os

import docker
from docker import types
from docker.errors import APIError

from lsdsuite.ThreadWithReturnValue.ThreadWithReturnValue import ThreadWithReturn
from .. import get_config, get_ssh, get_scp

log = logging.getLogger(__name__)

# Regex for parsing short-syntax port specification
# e.g.: 8080:80/tcp, 80:8080, 8080 (= 8080:8080)
# TODO: doesn't support advanced features such as port ranges
PORT_REGEX = re.compile(r"^(\d+)(?::(\d+))?(?:/(udp|tcp))?$")

# Was previously a field in config.yaml, but was removed since it never changes
DOCKER_SOCK = "/var/run/docker.sock"


class Engine(object):
    def __init__(self, config=None, client=None):
        from os.path import join

        if config is None:
            config = {}

        self.config = config = get_config(config)
        log.debug("Config: %s", config)

        self.lsds_dir = config['lsds_dir']
        self.logs_dir = join(self.lsds_dir, 'logs')
        self.registry_dir = join(self.lsds_dir, 'registry')
        self.log_address = 'unix://' + join(self.lsds_dir, 'logs.sock')

        self.ntp_sync_image = config['ntp_sync_image']
        self.slave_image = config['slave_image']
        self.ipam_plugin = config['ipam_plugin']
        self.ipam_server = config['ipam_server']

        self.slave_port = config['slave_port']
        self.ipam_port = config['ipam_port']

        if not client:
            client = docker.APIClient(version='auto')
        elif type(client) is docker.client.DockerClient:
            client = client.api
        self.client = client

        # Resource cache
        self._cache = {cls: dict() for cls in [Node, Network, Service, Task]}

        # Getter methods for a single resource
        self._get = {
            Node: client.inspect_node,
            Network: client.inspect_network,
            Service: client.inspect_service,
            Task: client.inspect_task
        }

        # Getter methods for resource lists
        self._list = {
            Node: client.nodes,
            Network: client.networks,
            Service: client.services,
            Task: client.tasks
        }

    def list(self, cls, filters=None):
        data = self._list[cls](filters=filters)
        return [self._update_cache(cls, d) for d in data]

    def get(self, cls, id):
        data = self._get[cls](id)
        return self._update_cache(cls, data)

    def nodes(self, **filters):
        # TODO: filter out nodes that aren't ready?
        return self.list(Node, filters)

    def node(self, id):
        return self.get(Node, id)

    def networks(self, **filters):
        return self.list(Network, filters)

    def network(self, id):
        return self.get(Network, id)

    @property
    def managed_networks(self):
        return self.networks(label='org.lsdsuite.app.id')

    def services(self, **filters):
        return self.list(Service, filters)

    def service(self, id):
        return self.get(Service, id)

    @property
    def managed_services(self):
        return self.services(label='org.lsdsuite.app.id')

    def tasks(self, **filters):
        return self.list(Task, filters)

    def task(self, id):
        return self.get(Task, id)

    def send(self, command, **params):
        return [node.send(command, **params) for node in self.nodes()]

    def send_command(self, command, **params):
        return [node.send_command(command, **params) for node in self.nodes()]

    def parallel_send(self, command, **params):
        threads = []
        for node in self.nodes():
            t = ThreadWithReturn(target=node.send,
                                 args=(command,),
                                 kwargs=params,
                                 name=str(node))
            log.debug("Starting thread %s...", node)
            t.start()
            threads.append(t)
        results = []
        for t in threads:
            log.debug("Waiting for thread %s...", t.name)
            results.append(t.join())
        return results

    def parallel_send_command(self, command, **params):
        threads = []
        for node in self.nodes():
            t = ThreadWithReturn(target=node.send_command,
                                 args=(command,),
                                 kwargs=params,
                                 name=str(node))
            log.debug("Starting thread %s...", node)
            t.start()
            threads.append(t)
        results = []
        for t in threads:
            log.debug("Waiting for thread %s...", t.name)
            results.append(t.join())
        return results

    def prune(self):
        log.info("Cleanup:")
        for service in self.managed_services:
            service.remove()
            log.info("Removed %s", service)

        for network in self.managed_networks:
            network.remove()
            log.info("Removed %s", network)

    def update_node(self, node):
        spec = node['Spec']
        self.client.update_node(node.id, node.version, spec)
        node.reload()

    def remove_network(self, id):
        self.client.remove_network(id)

    def remove_service(self, id):
        self.client.remove_service(id)

    def update_service(self, service):
        """Update a service's configuration.

        Mainly used for scaling it up/down.
        """
        spec = service['Spec']
        self.client.update_service(service.id, service.version,
                                   task_template=spec.get('TaskTemplate'),
                                   name=spec.get('Name'),
                                   labels=spec.get('Labels'),
                                   mode=spec.get('Mode'),
                                   update_config=spec.get('UpdateConfig'),
                                   networks=spec.get('Networks'),
                                   endpoint_spec=spec.get('EndpointSpec'))
        service.reload()

    @staticmethod
    def _node_do_ssh(node, cmd, check=True):
        with get_ssh(node) as ssh:
            _, _, stderr = ssh.exec_command(cmd)

            status = stderr.channel.recv_exit_status()
            if status == 0:
                return True

            if check:
                error = ""
                for line in stderr:
                    error += line
                raise APIError(error)

            return False

    def _node_leave_swarm(self, node, check=True):
        cmd = "docker swarm leave --force"
        return self._node_do_ssh(node, cmd, check=check)

    def _node_join_swarm(self, node, manager_ip, token, check=True):
        cmd = "docker swarm join --token '{token}' '{address}'"
        cmd = cmd.format(token=token, address=manager_ip)
        if not self._node_do_ssh(node, cmd, check=check):
            return False
        else:
            return self._node_create_dirs(node, check=check)

    def _node_create_dirs(self, node, check=True):
        cmd = "mkdir -p '{}'".format(self.registry_dir)
        return self._node_do_ssh(node, cmd, check=check)

    def _cluster_is_init(self):
        try:
            self.client.inspect_swarm()
            return True
        except APIError:
            return False

    # returns events, maxID, hosts
    #
    # @events hashmap. key ID, value Array of JSON objects
    # with "ID" = { "Host" , "Action" , "Processed": }
    #
    # @maxID: Integer
    #
    # @hosts: Array of strings of hosts
    def get_processed_events(self):
        import json
        nodes = self.nodes()

        max_id = 0
        ids_processor = {}
        hosts = []
        for node in nodes:
            hostname = node.hostname
            hosts += [hostname]
            status, result = node.send_command("processed_moments")

            events = json.loads(result)
            for event in events:
                error = event.get("error", None)
                if error is None:
                    id = int(event["ID"])
                    action = event["Action"]
                    processed = bool(event["Processed"])
                    info = ids_processor.get(id, [])
                    event_for_host = {"Host": hostname, "Action": action, "Processed": processed}
                    ids_processor[id] = info + [event_for_host]
                    if id > max_id:
                        max_id = id
                else:
                    log.warning("There was an error in slave creating processed events " + str(error))
        return ids_processor, max_id, hosts
    # remote_path is whete the faults folder is located in each node
    def cluster_status(self, container_path):
        if not self._cluster_is_init():
            return None

        config_nodes = self.config['nodes']
        manager = config_nodes[0]
        swarm_nodes = {n.ip: n for n in self.nodes()}

        status = []
        for node in config_nodes:
            ok = True
            s = {k: None for k in
                 ['address', 'hostname', 'ssh', 'swarm', 'ready', 'slave', 'slave:version', 'slave:faults', 'ntp']}

            ip = s['address'] = node['address']

            if node is manager and not node.get('remote'):
                s['ssh'] = True
            else:
                try:
                    with get_ssh(node):
                        s['ssh'] = True
                except Exception as e:
                    # TODO: catch more specific exception
                    log.warning("Can't reach %s: %s", ip, e)
                    ok = s['ssh'] = False

            n = swarm_nodes.get(ip)
            if n is None:
                ok = s['swarm'] = False
            else:
                s['hostname'] = n.hostname
                s['swarm'] = True
                if n.ready:
                    s['ready'] = True
                else:
                    ok = s['ready'] = False
                try:
                    s['slave'] = n.status
                    s['slave:version'] = n.slave_version
                    s['slave:faults'] = n.faults_hash(container_path)
                    s['ntp'] = n.ntp_offset
                except Exception as e:
                    # TODO: catch more specific exception
                    log.warning("Can't reach %s: %s", ip, e)
                    ok = s['slave'] = False

            s['ok'] = ok
            status.append(s)

        return status

    def cluster_init(self, force=False):
        from os import makedirs

        manager = self.config['nodes'][0]
        try:
            log.debug("Initializing Swarm @ %s", manager['address'])
            self.client.init_swarm(advertise_addr=manager['address'],
                                   force_new_cluster=force)
        except APIError as e:
            log.error("Couldn't initialize Swarm: %s", e)
            raise e

        if manager.get('remote'):
            self._node_create_dirs(manager, check=True)
        else:
            makedirs(self.registry_dir, exist_ok=True)

    def cluster_down(self):
        nodes = self.config['nodes'][1:]

        for node in nodes:
            log.debug("Forcing %s to leave Swarm", node['address'])
            self._node_leave_swarm(node, check=False)

        for node in self.nodes():
            if not node.manager:
                log.debug("Removing %s from Swarm", node.ip)
                self.client.remove_node(node.id, force=True)

        log.debug("Leaving Swarm")
        self.client.leave_swarm(force=True)

    def cluster_up(self, local_faults_folder, faults_folder_in_host, faults_folder_in_container, force=False):
        nodes = self.config['nodes']
        manager, nodes = nodes[0], nodes[1:]

        if not self._cluster_is_init():
            self.cluster_init()

        token = self.client.inspect_swarm()
        token = token['JoinTokens']['Worker']

        log.debug("Removing old nodes from Swarm")
        for node in self.nodes():
            if node.ip in [n['address'] for n in nodes + [manager]]:
                if node.ready:
                    continue

            log.debug("Removing %s from Swarm", node.ip)
            self.client.remove_node(node.id, force=force)

        for node in nodes:
            if force:
                log.debug("Forcing %s to leave Swarm", node['address'])
                self._node_leave_swarm(node, check=False)
            elif node['address'] in [n.ip for n in self.nodes()]:
                # Don't re-join node
                continue

            try:
                log.debug("Adding %s to the Swarm", node['address'])
                self._node_join_swarm(node, manager['address'], token)
            except APIError as e:
                log.error("Node %s can't join Swarm: %s", node['address'], e)
                raise e

        log.info("Copying Faults from: %s", local_faults_folder)
        self.copy_faults(local_faults_folder, faults_folder_in_host)
        log.info("IGNROING Start Service Registry")
        # self.start_registry(restart=True)
        # self.services(name='registry')[0].wait()
        log.info("Start Slave Service")
        self.start_slave(faults_folder_in_host, faults_folder_in_container, restart=True)
        self.services(name='lsdsuite-slave')[0].wait()
        log.info("Waiting 10 seconds for slaves to come up")
        time.sleep(10)
        log.info("Starting IPAM Service (network related)")
        self.start_ipam(restart=True)
        self.services(name='lsdsuite-ipam')[0].wait()

    def copy_faults(self, local_path, remote_path):
        nodes = self.config['nodes']
        for node in nodes:
            cmd = "mkdir -p {dir}".format(dir=remote_path)
            # in case of error it will raise Error
            self._node_do_ssh(node, cmd, check=True)
            with get_scp(node) as scp:
                files = [os.path.join(local_path, base_filename)
                         for base_filename in os.listdir(local_path)]
                scp.put(files, recursive=True, remote_path=remote_path)

    def inject_faults_volumes(self, service_spec, faults_folder_in_host, faults_folder_in_container):
            log.debug("Injecting Faults Volume in: ", service_spec)
            volumes = service_spec.get('volumes', [])

            faults_volume = {'type': 'bind',
                             'read_only': True,
                             'source': faults_folder_in_host,
                             'target': faults_folder_in_container}
            volumes.append(faults_volume)
            service_spec['volumes'] = volumes

    def start_ntp_sync(self):
        """Creates and runs faultsee-ntp-sync service on all nodes"""

        # capabilities in docker swarm only comes out in version 19.06 of Docker,
        # so we will "manually" launch a container on each slave
        log.info("Synchronizing Clocks")
        results = self.parallel_send("ntp_sync", **{"docker_image": self.ntp_sync_image})
        if not all(results):
            log.warning("There was an error syncing NTP (IGNORING it). check slave logs for details.")

    def start_slave(self, faults_folder_in_host, faults_folder_in_container, restart=False):
        """Creates and runs lsdsuite-slave service on all nodes."""
        service, = self.services(name='lsdsuite-slave') or [None]
        if service:
            if restart:
                service.remove()
                time.sleep(10)
            else:
                return service

        # Can't do this if slave is down...
        # self.send('pull', image=self.slave_image)

        spec = {
            'image': self.slave_image,
            'environment': {'HOST_PROC': "/app/proc",
                            'HOST_SYS': "/app/sys"},
            'volumes': [{'type': 'bind',
                         'source': DOCKER_SOCK,
                         'target': "/var/run/docker.sock"},
                        {'type': 'bind',
                         'source': self.lsds_dir,
                         'target': "/out"},
                        {'type': 'bind',
                         'read_only': True,
                         'source': "/proc",
                         'target': "/app/proc"},
                        {'type': 'bind',
                         'read_only': True,
                         'source': "/sys",
                         'target': "/app/sys"}],
            'networks': ['host'],  # = --network=host
            'deploy': {
                'mode': 'global',
                'restart_policy': {
                    'condition': 'any',
                    'delay': 5000000000,
                    'max_attempts': 0
                },
            },
            'ports': [{'mode': 'host',
                       'target': 7000,
                       'published': self.slave_port}]
        }
        self.inject_faults_volumes(spec, faults_folder_in_host, faults_folder_in_container)
        spec = {'services': {'lsdsuite-slave': spec}}
        args = self._spec_to_service('lsdsuite-slave', spec)
        # Remove logging config
        args['task_template'].pop('LogDriver')

        service = self.client.create_service(**args)
        service = self.service(service['ID'])
        return service

    def stop_slave(self):
        """Stops lsdsuite-slave service."""
        service, = self.services(name='lsdsuite-slave') or [None]
        if service:
            service.remove()

    def start_registry(self, restart=False):
        """Creates and runs registry service."""
        service, = self.services(name='registry') or [None]
        if service:
            if restart:
                service.remove()
                time.sleep(10)
            else:
                return service

        spec = {
            'image': "registry",
            'deploy': {
                'mode': 'replicated',
                'replicas': 1,
                'restart_policy': {
                    'condition': 'any',
                    'delay': 5000000000,
                    'max_attempts': 0
                },
                'placement': {
                    'constraints': ['node.role == manager']
                }
            },
            'volumes': [{'type': 'bind',
                         'source': self.registry_dir,
                         'target': "/var/lib/registry"}],
            'ports': [{'target': 5000,
                       'published': 5000}]
        }

        spec = {'services': {'registry': spec}}
        args = self._spec_to_service('registry', spec)
        # Remove logging config
        args['task_template'].pop('LogDriver')

        service = self.client.create_service(**args)
        service = self.service(service['ID'])
        return service

    def start_ipam(self, restart=False):
        """Creates and runs IPAM service, installs plugin."""
        service, = self.services(name='lsdsuite-ipam') or [None]
        if service:
            if restart:
                service.remove()
                time.sleep(10)
            else:
                return service

        spec = {
            'image': self.ipam_server,
            'deploy': {
                'mode': 'replicated',
                'replicas': 1,
                'restart_policy': {
                    'condition': 'any',
                    'delay': 5000000000,
                    'max_attempts': 0
                },
                'placement': {
                    'constraints': ['node.role == manager']
                }
            },
            'ports': [{'target': 7001,
                       'published': self.ipam_port}]
        }

        spec = {'services': {'lsdsuite-ipam': spec}}
        args = self._spec_to_service('lsdsuite-ipam', spec)
        # Remove logging config
        args['task_template'].pop('LogDriver')

        service = self.client.create_service(**args)
        service = self.service(service['ID'])

        # Install plugin on all nodes
        for i, node in enumerate(self.nodes()):
            # TODO: check for errors
            node.send('ipam', id=str(i),
                      image=self.ipam_plugin,
                      port=str(self.ipam_port),
                      logs=self.logs_dir)

        return service

    def create_app(self, name, spec):
        """Creates App from spec.

        Creates all networks and in spec and returns app.
        """
        app = App(self, name)
        # TODO: create implicit network if none is provided?

        log.info('Creating %s...', app)
        # Pull images before creating services
        # only pull images one time
        pulled_images = {}
        for service in spec['services']:
            image = spec['services'][service].get('image')
            if not image:
                msg = "Service {}: no image specified".format(service)
                log.error(msg)
                raise ValueError(msg)

            log.debug('Pulling image %s...', image)
            if not pulled_images.get(image, False):
                # TODO: check return value
                answers = self.parallel_send('pull', image=image)
                print("Pull answers: ", answers)
                pulled_images[image] = True
                for answer in answers:
                    if answer == False:
                        raise ValueError("Failed to pull image: " + str(image))

        try:
            for network in spec.get('networks', {}):
                log.debug('Creating network %s...', network)
                self.create_network(app, network, spec)

            for service, service_spec in spec['services'].items():
                log.debug('Creating service %s...', service)
                service_spec['labels'] = service_spec.get('labels') or {}
                service_spec['labels'].update(**{
                    'org.faultsee.experiment.container': "true",
                })
                self.create_service(app, service, spec)

        except APIError as e:
            app.remove()
            raise e

        log.info("%s created", app)
        return app

    def create_network(self, app, name, spec):
        args = self._spec_to_network(name, spec)

        if not args:
            # 'external', return existing network
            network = self.network(name)
            return network

        args['labels'] = args.get('labels') or {}
        args['labels'].update(**{
            'org.lsdsuite.app.id': app.id,
            'org.lsdsuite.app.name': app.name,
        })
        log.debug("Args Network: " + str(args))
        network = self.client.create_network(**args)
        log.debug("Network created: " + str(network))
        network = self.network(network['Id'])

        return network

    def create_service(self, app, name, spec):
        args = self._spec_to_service(name, spec)
        args['labels'] = args.get('labels') or {}
        args['labels'].update(**{
            'org.lsdsuite.app.id': app.id,
            'org.lsdsuite.app.name': app.name,
        })
        log.debug("%s", args)

        service = self.client.create_service(**args)
        service = self.service(service['ID'])

        return service

    def _spec_to_network(self, name, spec):
        """Converts a YAML spec to an arguments dict
        for docker.APIClient.create_network
        """
        spec = spec['networks'][name] or {}

        if spec.get('external'):
            # external means use existing network
            # 2 different forms:
            # networks:
            #   my-network:
            #     external: true
            #
            # networks:
            #   name-inside-spec:
            #     external:
            #       name: actual-name-of-network
            #
            # TODO: only 1st form is supported for now
            # real_name = spec.get('external', {}).get('name', name)
            # return real_name, name

            return None

        ipam = spec.get('ipam', {})
        pool_configs = []
        for config in ipam.get('config', []):
            subnet = config.get('subnet')
            if subnet:
                config = types.IPAMPool(subnet=subnet)
                pool_configs.append(config)
                # TODO: iprange, gateway, aux_addresses
                # these aren't in the Docker compose spec, but we should make
                # a special exception for lsdsuite-ipam

        # faultsee-ipam is the name of the plugin installed locally on each host
        # this name is hardcoded in slave code
        ipam = types.IPAMConfig(
            driver=ipam.get('driver', 'faultsee-ipam:latest'),
            pool_configs=pool_configs
        )

        return dict(
            name=name,
            driver=spec.get('driver', 'overlay'),
            options=spec.get('driver_opts'),
            ipam=ipam,
            check_duplicate=None,  # TODO: set to True?
            internal=spec.get('internal'),
            # TODO: parse list-of-strings label syntax
            labels=spec.get('labels'),
            # enable_ipv6=spec.get('enable_ipv6'),  # Not supported in Swarm
            attachable=spec.get('attachable'),
            scope='swarm'
        )

    def make_restart_policy_none(self, service_spec):
        depl = service_spec.get('deploy', {})

        restart_policy = depl.get('restart_policy', {})
        restart_policy_condition = restart_policy.get('condition', None),
        if restart_policy_condition is not None:
            if restart_policy_condition != "none":
                log.warning("FaultSee only works when containers restart policy is set to none, will change provided value")

        restart_policy = types.RestartPolicy(
            # Docker default condition is 'any'
            condition="none",
        )
        depl["restart_policy"] = restart_policy
        service_spec["deploy"] = depl

    def _spec_to_service(self, name, spec):
        """Converts a YAML spec to an arguments dict
        for docker.APIClient.create_service
        """
        spec = spec['services'][name]
        depl = spec.get('deploy', {})


        mounts = []
        for mount in spec.get('volumes', []):
            if type(mount) is str:
                mount = types.Mount.parse_mount_string(mount)
            else:
                mount = types.Mount(
                    source=mount['source'],
                    target=mount['target'],
                    type=mount.get('type', 'volume'),
                    read_only=mount.get('read_only', False),
                    # TODO: propagation
                    # TODO: no_copy
                    # TODO: labels
                    # TODO: driver_config
                )
            mounts.append(mount)

        ports = []
        for port in spec.get('ports', []):
            if type(port) is str:
                m = PORT_REGEX.match(port)
                if not m:
                    raise ValueError("Can't parse port specification " + port)

                target, published, protocol = m.groups()
                port = dict(
                    target=int(target),
                    published=int(published),
                    protocol=protocol
                )

            port = {
                'Protocol': port.get('protocol'),
                'PublishMode': port.get('mode'),
                'PublishedPort': port.get('published'),
                'TargetPort': port.get('target')
            }
            ports.append(port)

        container_spec = types.ContainerSpec(
            image=spec.get('image'),
            command=spec.get('command'),
            args=spec.get('args'),  # not in compose spec
            hostname=spec.get('hostname'),
            env=spec.get('environment'),
            # TODO: dir=spec.get('working_dir'),
            user=spec.get('user'),
            # TODO: parse list-of-strings label syntax
            labels=spec.get('labels'),
            mounts=mounts,
            stop_grace_period=spec.get('stop_grace_period'),
            # TODO: secrets
            tty=spec.get('tty'),

            # TODO: groups
            # TODO: open_stdin=spec.get('stdin_open'),
            # TODO: healthcheck
            # TODO: hosts=spec.get('extra_hosts'),
            # TODO: dns_config
            # TODO: configs
            # TODO: privileges
        )

        log_driver = types.DriverConfig(
            name='syslog',
            options={'syslog-address': self.log_address,
                     'syslog-format': 'rfc5424micro',
                     'tag': '{{.FullID}}'}
        )

        def parse_cpu(cpu):
            if not cpu:
                return None
            return int(float(cpu) * 10 ** 9)

        def parse_mem(mem):
            import re
            pattern = "(\d+)([kKmMgG]{0,1})(i[bB]|[bB]){0,1}"

            if not mem:
                return None

            matches = re.match(pattern, mem)
            if matches == None:
                log.warn("Cannot parse memory: %s. Will consider it NONE", mem)
                return None

            result = re.split(pattern, mem)

            # default Bytes
            multiplication_factor = 1
            # 1KB = 1000B
            order_up_multiplication_factor = 1000

            number = result[1]
            unit = result[2]
            bytesOrBites = result[3]

            if bytesOrBites is not None:
                includesI = bytesOrBites[0] == "i"
                if includesI:
                    # 1 KiB = 1024B
                    order_up_multiplication_factor = 1024

            if unit is not None:
                if unit.lower() == "k":
                    multiplication_factor = order_up_multiplication_factor
                if unit.lower() == "m":
                    multiplication_factor = order_up_multiplication_factor * order_up_multiplication_factor
                if unit.lower() == "g":
                    multiplication_factor = order_up_multiplication_factor * order_up_multiplication_factor * order_up_multiplication_factor

            return int(number) * multiplication_factor

        lim = depl.get('resources', {}).get('limits', {})
        res = depl.get('resource', {}).get('reservations', {})
        resources = types.Resources(
            cpu_limit=parse_cpu(lim.get('cpus')),
            mem_limit=parse_mem(lim.get('memory')),
            cpu_reservation=parse_cpu(res.get('cpus')),
            mem_reservation=parse_mem(res.get('memory'))
        )

        restart_policy = depl.get('restart_policy', {})
        restart_policy = types.RestartPolicy(
            # Docker default condition is 'any'
            condition=restart_policy.get('condition', 'none'),
            delay=restart_policy.get('delay'),  # TODO: parse duration
            max_attempts=restart_policy.get('max_attempts'),
            window=restart_policy.get('window')  # TODO: parse duration
        )

        placement = depl.get('placement', {})
        placement = types.Placement(
            constraints=placement.get('constraints'),
            preferences=placement.get('preferences')
        )

        task_template = types.TaskTemplate(
            container_spec=container_spec,
            log_driver=log_driver,
            resources=resources,
            restart_policy=restart_policy,
            placement=placement
            # TODO: force_update
        )

        service_mode = types.ServiceMode(
            mode=depl.get('mode', 'replicated'),
            replicas=depl.get('replicas')
        )

        endpoint_spec = types.EndpointSpec(
            mode=depl.get('endpoint_mode'),
            ports=ports
        )

        return dict(
            task_template=task_template,
            name=name,
            # TODO: parse list-of-strings label syntax
            labels=spec.get('deploy', {}).get('labels'),
            mode=service_mode,
            # TODO: update_config
            networks=spec.get('networks', []),
            endpoint_spec=endpoint_spec
        )

    def _update_cache(self, cls, data):
        id = data.get('ID') or data.get('Id')
        cache = self._cache[cls]
        if id in cache:
            cache[id].update(**data)
        else:
            cache[id] = cls(self, data)

        return cache[id]


class App(object):
    def __init__(self, engine, name=None):
        import uuid
        self.id = uuid.uuid4().hex

        self.engine = engine
        self.name = name
        self.label_selector = "org.lsdsuite.app.id={}".format(self.id)

    # def send_start_to_all_nodes(self):
    #     self.engine.send("start_run")

    def send_dry_run_to_all_nodes(self):
        self.engine.send("start_dry_run")

    def remove(self):
        log.info('Removing %s...', self)
        for service in self.services:
            service.remove()

        for network in self.networks:
            network.remove()

        log.info('%s removed', self)

    @property
    def networks(self):
        return self.engine.networks(label=self.label_selector)

    @property
    def services(self):
        return self.engine.services(label=self.label_selector)

    def service(self, id=None, name=None):
        result_for_debug = self.engine.services(id=id, name=name,
                                                label=self.label_selector) or [None]
        # first result will be the best
        service = result_for_debug[0]
        return service

    def __repr__(self):
        return "App[{id}]:{name}".format(id=self.id[:16], name=self.name)


class Resource(dict):
    """Base class for resources such as Tasks, Services, Networks, Node.

    Simply a wrapper around dicts returned by the Docker low-level API.
    """

    def __init__(self, engine, data):
        self.engine = engine
        self.update(**data)

    def reload(self):
        self.engine.get(type(self), self.id)
        return True

    @property
    def id(self):
        return self.get('ID') or self.get('Id')

    @property
    def version(self):
        return self.get('Version', {}).get('Index')

    def __repr__(self):
        return "{type}[{id}]".format(type=self.__class__.__name__,
                                     id=self.id[:16])

    def __eq__(self, other):
        if type(self) == type(other):
            return self.id == other.id
        else:
            return False

    def __hash__(self):
        return hash(self.id)


class Node(Resource):
    """Represents a Docker Swarm Node."""

    @property
    def ip(self):
        return self['Status']['Addr']

    def send(self, command, mapArrayStringParams={}, **params):
        """Sends a command to the lsdsuite-slave instance running on node.
        params transform all extra parameters into dictionary (need to be strings)
        mapArrayStringParams is a dictionary: (values must be list of strings)

        Returns True if command succeeded, False otherwise
        """
        status, msg = self.send_command(command, mapArrayStringParams, **params)
        return status == 'ok'

    def send_command(self, command, mapArrayStringParams={}, **params):
        """Sends a command to the lsdsuite-slave instance running on node.
        params transform all extra parameters into dictionary (need to be strings)
        mapArrayStringParams is a dictionary: (values must be list of strings)

        Returns he slave answer status and status message
        """
        import json
        import socket
        msg = json.dumps({'command': command, 'MapStringParams': params,
                          'MapArrayStringParams': mapArrayStringParams})
        log.debug("Send [%s] %s", self.ip, msg)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # TODO: catch "Connection refused" ?
            sock.connect((self.ip, self.engine.slave_port))
            sock.send(msg.encode())

            resp = b''
            while True:
                r = sock.recv(2 ** 10)
                if r:
                    resp += r
                else:
                    break

            resp = resp.decode()
            log.debug("Response [%s] %s", self.ip, resp.strip())
            resp = json.loads(resp)
            return resp.get('status'), resp.get('msg', None)

    @property
    def state(self):
        return self['Status']['State']

    @property
    def ready(self):
        return self.state == 'ready'

    @property
    def status(self):
        return self.send('status')

    @property
    def ntp_offset(self):
        status, offset = self.send_command('ntp_offset')
        if status == "ok":
            return offset
        else:
            return "Failed to Get NTP Offset"
    @property
    def slave_version(self):
        status, version = self.send_command('slave_version')
        if status == "ok":
            return version
        else:
            return "Failed To Get Version"

    def faults_hash(self, remote_path):
        status, received_hash = self.send_command('faults_hash', path=remote_path)
        if status == "ok":
            return received_hash
        else:
            return "Failed To Get Hash"

    @property
    def hostname(self):
        return self['Description']['Hostname']

    @property
    def role(self):
        return self['Spec']['Role']

    @property
    def manager(self):
        return self.role == 'manager'

    def __repr__(self):
        return super().__repr__() + ":" + self.ip


class Network(Resource):
    """Represents a Docker Network."""

    @property
    def name(self):
        return self['Name']

    def remove(self):
        self.engine.remove_network(self.id)

    def __repr__(self):
        return super().__repr__() + ":" + self.name


class Service(Resource):
    """Represents a Docker Swarm Service.

    Offers functionality to scale the service up/down, retrieve tasks, ...
    """

    @property
    def name(self):
        return self['Spec']['Name']

    @property
    def tasks(self):
        return self.engine.tasks(service=self.id)

    @property
    def live_tasks(self):
        return [t for t in self.tasks if t.running]

    @property
    def replicas(self):
        return len(self.live_tasks)

    @property
    def desired_replicas(self):
        return self['Spec']['Mode'].get('Replicated', {}).get('Replicas')

    @desired_replicas.setter
    def desired_replicas(self, n):
        if 'Replicated' not in self['Spec']['Mode']:
            log.warning("%s is not replicated, can't change desired_replicas",
                        self)
            return

        # NOTE: Docker re-balances tasks when doing this...

        self.reload()
        log.debug("%s: set desired_replicas from %d to %d",
                  self, self.desired_replicas, n)
        self['Spec']['Mode']['Replicated']['Replicas'] = n
        self.engine.update_service(self)

    @property
    def tasks_by_node(self):
        from collections import defaultdict

        tasks_by_node = defaultdict(list)
        for t in self.live_tasks:
            tasks_by_node[t.node].append(t)

        return dict(tasks_by_node)

    #
    # def print_tasks(self):
    #     lista = self.tasks
    #     tamanho = len(lista)
    #     print("Size=", tamanho)
    #     index = 0
    #     while index < tamanho:
    #         print("  ", lista[index])
    #         index += 1
    #     print("NExt")
    #
    #     for t in self.tasks:
    #         print("  ", t)
    #         print("  ", t.__dict__)
    #
    #     t = lista[0]
    #     for att in dir(t):
    #         print ("  ", "  ", att, getattr(t, att))
    #
    #     print(self.engine.tasks(service=self.id))

    def add(self, n, wait=True):
        """Adds `n` replicas and optionally waits for them to start."""
        log.debug("%s: add %d replicas", self, n)
        old_tasks = set(self.tasks)

        self.desired_replicas += n
        time.sleep(5)  # wait for Docker to register change
        if wait:
            self.wait()

        new_tasks = set(self.tasks)

        return list(new_tasks - old_tasks)

    def rm(self, n, signal="TERM", wait=True):
        """Removes `n` replicas and optionally waits for them to start."""
        log.debug("%s: remove %d replicas", self, n)
        old_tasks = set(self.tasks)

        self.desired_replicas -= n
        time.sleep(5)  # wait for Docker to register change
        if wait:
            self.wait()

        new_tasks = set(self.tasks)

        return list(new_tasks - old_tasks)

    def custom_fault(self, number_replicas, fault_details, fault_arguments, wait=False):
        """Selects `number_replicas` random replicas and sends a fault
            optionally waits for them to start.

            fault_details and fault_arguments are dictionaries with information required to execute a fault

            they are divided because Golang has types, and we need different variables for different types
            fault_details: map[string]string
            fault_arguments: map[string]list(string)

            fault_details : {
                "fault_file_name": "waste_cpu.sh",
                "fault_file_folder": "/home/pi/",
                "executable": "/usr/bin/python",
            }
            fault_arguments : {
                "executable_arguments": ["-c"],
                "fault_script_arguments": ["arg1", "arg2"]
            }
            """
        import random
        from collections import defaultdict

        log.debug("%s: custom fault in %d tasks", self, number_replicas)
        self.reload()

        alive_replicas = self.replicas
        if alive_replicas < number_replicas:
            log.error("%s: Can't send custom fault to %d tasks: only %d are alive",
                      self, number_replicas, alive_replicas)
            number_replicas = alive_replicas

        tasks_by_node = self.tasks_by_node
        targets = []
        for i in range(number_replicas):
            # find node with most tasks
            tasks = max(tasks_by_node.values(), key=len)
            t = random.choice(tasks)
            targets.append(t)
            tasks.remove(t)

        # if self.engine.config['mono_kill']:
        #     for t in kills:
        #         log.debug('Killing %s...', t)
        #         t.kill(signal=signal)
        #     return

        targets_by_node = defaultdict(list)
        for t in targets:
            targets_by_node[t.node].append(t)

        # FIXME change kill_batch to batch_size
        # Divide each node's tasks in batches of size N
        N = self.engine.config['kill_batch']
        batches = {}
        for node, tasks in targets_by_node.items():
            batches[node] = [tasks[i:i + N] for i in range(0, len(tasks), N)]

        # Slices of commands to send:
        # [(node1-batch1, node2-batch1, node3-batch1, ...),
        #  (node1-batch2, node2-batch2, ...), ...]
        slices = []
        while True:
            slice = {}
            for node, tasks in batches.items():
                if not tasks:
                    continue
                slice[node] = tasks.pop(0)
            if not slice:
                break
            slices.append(slice)

        def thread(node, tasks, fault_details, fault_arguments):
            # TODO: refactor engine.send() to return the result sent back by
            # slave (instead of True/False). For 'kill', slave returns list of
            # killed containers; compare this list to `tasks`.
            log.debug("%s: custom_fault in %d tasks @ %s",
                      self, len(tasks), node)

            ids = str.join(',', (t.container[:16] for t in tasks))
            if node.send('custom', id=ids, mapArrayStringParams=fault_arguments, **fault_details):
                log.debug("Custom fault injected: {} : {}".format(
                    fault_details, fault_arguments))
            else:
                log.error("Couldn't order CPU waste")

        for slice in slices:
            threads = []
            for node, tasks in slice.items():
                t = threading.Thread(target=thread,
                                     args=(node, tasks, fault_details,
                                           fault_arguments),
                                     name=str(node))
                log.debug("Starting thread %s...", node)
                t.start()
                threads.append(t)

            for t in threads:
                log.debug("Waiting for thread %s...", t.name)
                t.join()

        return

    def kill(self, n, signal='TERM'):
        """Kills `n` tasks with signal `signal`

        Works by selecting the node with the most tasks, selecting a random
        task, and sending a "kill" command.
        """
        import random
        from collections import defaultdict

        log.debug("%s: Kill %d tasks", self, n)
        self.reload()

        replicas = self.replicas
        if replicas < n:
            log.error("%s: Can't kill %d tasks: only %d are alive",
                      self, n, replicas)
            n = replicas

        tasks_by_node = self.tasks_by_node
        kills = []
        for i in range(n):
            # find node with most tasks
            tasks = max(tasks_by_node.values(), key=len)
            t = random.choice(tasks)
            kills.append(t)
            tasks.remove(t)

        if self.engine.config['mono_kill']:
            for t in kills:
                log.debug('Killing %s...', t)
                t.kill(signal=signal)
            return

        kills_by_node = defaultdict(list)
        for t in kills:
            kills_by_node[t.node].append(t)

        # Divide each node's tasks in batches of size N
        N = self.engine.config['kill_batch']
        batches = {}
        for node, tasks in kills_by_node.items():
            batches[node] = [tasks[i:i + N] for i in range(0, len(tasks), N)]

        # Slices of commands to send:
        # [(node1-batch1, node2-batch1, node3-batch1, ...),
        #  (node1-batch2, node2-batch2, ...), ...]
        slices = []
        while True:
            slice = {}
            for node, tasks in batches.items():
                if not tasks:
                    continue
                slice[node] = tasks.pop(0)
            if not slice:
                break
            slices.append(slice)

        def thread(node, tasks):
            # TODO: refactor engine.send() to return the result sent back by
            # slave (instead of True/False). For 'kill', slave returns list of
            # killed containers; compare this list to `tasks`.
            log.debug("%s: Killing %d tasks @ %s",
                      self, len(tasks), node)

            ids = str.join(',', (t.container[:16] for t in tasks))
            if node.send('kill', id=ids, signal=signal):
                log.debug("Tasks killed!")
            else:
                log.error("Couldn't kill tasks")

        for slice in slices:
            threads = []
            for node, tasks in slice.items():
                t = threading.Thread(target=thread,
                                     args=(node, tasks),
                                     name=str(node))
                log.debug("Starting thread %s...", node)
                t.start()
                threads.append(t)

            for t in threads:
                log.debug("Waiting for thread %s...", t.name)
                t.join()

        return

    def remove(self):
        """Terminates service."""
        self.engine.remove_service(self.id)

    def wait(self, sleep=0.5, max_sleep=None):
        """Waits for tasks to start/terminate.

        Loops until all tasks reached their expected state (and returns True),
        or a delay of max_sleep has been reached (and returns False)
        """
        total_sleep = 0
        while not all(t.ok for t in self.tasks):
            log.debug("%s: wait: %d/%d", self,
                      sum(t.ok for t in self.tasks),
                      len(self.tasks))
            time.sleep(sleep)
            total_sleep += sleep
            if max_sleep and total_sleep >= max_sleep:
                log.debug("%s: wait: timeout", self)
                return False
        else:
            return True

    def __repr__(self):
        return super().__repr__() + ":" + self.name


class Task(Resource):
    """Represents a Docker Swarm Task.

    (i.e. a container running on a node as part of a service)
    """

    @property
    def state(self):
        return self['Status']['State']

    @property
    def desired_state(self):
        return self['DesiredState']

    @property
    def running(self):
        """Is this task running?"""
        return self.state == 'running'

    @property
    def ok(self):
        """Does this task's state match its desired state?"""
        if self.desired_state == 'running':
            return self.state == 'running'
        else:
            return self.state != 'running'

    @property
    def container(self):
        """ID of this task's container"""
        return self['Status']['ContainerStatus'].get('ContainerID')

    @property
    def node_id(self):
        """ID of the node this task is running on"""
        return self.get('NodeID')

    @property
    def node(self):
        """Node this task is running on"""
        id = self.node_id
        if id is None:
            return None
        else:
            return self.engine.node(self.node_id)

    @property
    def service_id(self):
        return self['ServiceID']

    def kill(self, signal='TERM'):
        return self.node.send('kill', id=self.container, signal=signal)

    def wait(self, sleep=0.5, max_sleep=None):
        """Waits until task's desired state matches its state

        Loops until task starts/stops running (and returns True),
        or a delay of max_sleep has been reached (and returns False)
        """
        self.reload()
        total_sleep = 0
        while not self.ok:
            self.reload()
            log.debug("%s: wait: %s/%s", self, self.state, self.desired_state)
            time.sleep(sleep)
            total_sleep += sleep
            if max_sleep and total_sleep >= max_sleep:
                log.debug("%s: wait: timeout", self)
                return False
        else:
            return True

    def __repr__(self):
        return (super().__repr__()
                + "({})".format((self.container or "None            ")[:16])
                + "@" + repr(self.node))
