import sys
import os

DEFAULT_CONFIG = {
    'nodes': [
        {'address': '127.0.0.1'}
    ]
}


def get_config(config):
    config = dict(DEFAULT_CONFIG, **config)

    config['lsds_dir'] = os.path.abspath(os.environ['LSDS_DIR'])
    config['ntp_sync_image'] = os.environ['LSDS_NTP_SYNC_IMAGE']
    config['slave_image'] = os.environ['LSDS_SLAVE']
    config['ipam_plugin'] = os.environ['LSDS_IPAM_PLUGIN']
    config['ipam_server'] = os.environ['LSDS_IPAM_SERVER']

    config['faults_folder_container'] = os.environ['LSDS_FAULTS_FOLDER_CONTAINER']
    config['faults_folder_host'] = os.environ['LSDS_FAULTS_FOLDER_HOST']
    config['faults_folder_local'] = os.environ['LSDS_FAULTS_FOLDER_LOCAL']

    config['slave_port'] = int(os.environ['LSDS_SLAVE_PORT'])
    config['ipam_port'] = int(os.environ['LSDS_IPAM_PORT'])

    config['mono_kill'] = bool(os.environ.get('LSDS_MONO_KILL'))
    config['kill_batch'] = int(os.environ.get('LSDS_KILL_BATCH', 1000))

    # TODO: Check values (e.g. 0 < ports <= 65536)
    return config


def get_ssh(node):
    from paramiko import SSHClient, WarningPolicy

    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(WarningPolicy())
    ssh.connect(node.get('address'),
                username=node.get('username'),
                password=node.get('password'),
                key_filename=node.get('private_key'))

    return ssh


def get_scp(node):
    from scp import SCPClient
    ssh = get_ssh(node)
    scp = SCPClient(ssh.get_transport())
    return scp
