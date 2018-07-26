import click
import yaml
import logging
import os
import hashlib

import lsdsuite
from lsdsuite.benchmark import Benchmark
from lsdsuite.engine.docker import Engine
from lsdsuite.parser.parse import Parser
from . import get_config

from .__version__ import __version__

@click.group()
@click.version_option('0.0.1')
@click.option('-v', '--verbose', is_flag=True,
              help="Print debug messages.")
@click.option('--engine', type=click.Choice(['docker']), default='docker',
              help="Container engine.")
@click.option('--config', type=click.File('r'), default="./config.yaml",
              help="Cluster configuration file.")
@click.pass_context
def cli(ctx, **kwargs):
    print("FaultSee - Master Container - Version: " + str(__version__))
    """LSDSuite.
    TODO
    """
    ctx.obj = kwargs
    config = yaml.load(ctx.obj['config'])

    if ctx.obj['engine'] == 'docker':
        ctx.obj['engine'] = Engine(config)
    else:
        click.echo("Unsupported engine '{}'".format(ctx.obj['engine']))
        exit(-1)

    ctx.obj['config'] = ctx.obj['engine'].config

    if ctx.obj['verbose']:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig()
    for log in [lsdsuite.benchmark.log,
                lsdsuite.churn.log,
                lsdsuite.engine.docker.log,
                lsdsuite.parser.parse.log]:
        log.setLevel(level)


@cli.group()
@click.pass_context
def cluster(ctx):
    """Manages cluster."""


@cluster.command('init')
@click.pass_context
def cluster_init(ctx):
    """Only initialize Swarm manager."""
    engine = ctx.obj['engine']
    click.echo("Initializing Swarm manager")
    engine.cluster_init()
    click.echo("Cluster initialized!")


@cluster.command('up')
@click.option('-f', '--force', is_flag=True,
              help="Force re-initialization.")
@click.pass_context
def cluster_up(ctx, force):
    """Set cluster up."""
    engine = ctx.obj['engine']

    config = get_config({})
    click.echo("Setting up Swarm")

    engine.cluster_up(local_faults_folder=config['faults_folder_local'], faults_folder_in_host=config['faults_folder_host'], faults_folder_in_container=config['faults_folder_container'], force=force)

    click.echo("Cluster up!")


@cluster.command('down')
@click.pass_context
def cluster_down(ctx):
    """Tear cluster down."""
    ctx.obj['engine'].cluster_down()
    click.echo("Cluster down!")


@cluster.command('registry')
@click.pass_context
def cluster_registry(ctx):
    """Create private registry service."""
    ctx.obj['engine'].start_registry().wait()
    click.echo("Registry created!")


@cluster.command('ntp')
@click.pass_context
def cluster_sync_ntp(ctx):
    """Create private registry service."""
    _cluster_status(ctx)
    ctx.obj['engine'].start_ntp_sync()
    _cluster_status(ctx)


@cluster.command('status')
@click.pass_context
def cluster_status(ctx):
    _cluster_status(ctx)


def _cluster_status(ctx):
    """Print cluster status."""
    FORMAT = ("{address:<15} {hostname:<20} {ssh:<8}"
              "{swarm:<8} {ready:<8} {slave:<8} {slave_version:<14} {slave_faults_hash:<14} {ntp:>15} {ok:<8}")

    def print_header():
        click.echo(FORMAT.format(address="ADDRESS",
                                 hostname="HOSTNAME",
                                 ssh="SSH?",
                                 swarm="SWARM?",
                                 ready="READY?",
                                 slave="SLAVE?",
                                 slave_version="SLAVE_Version",
                                 slave_faults_hash="SLAVE_Faults",
                                 ntp="NTP OFFSET (ms)",
                                 ok="OK?"))

    def print_node(node, local_hash_version):
        def unbool(x):
            if x:
                return click.style("OK      ", fg='green')
            else:
                return click.style("NO      ", fg='red')

        def compare_hash(local, received):
            #TODO FORMAT
            hashes_equal = local == received

            received = str(received)
            if len(received) > 13:
                received = received[:12]
            hash_status_string = '{:<14s}'.format(received)

            if hashes_equal:
                return click.style(hash_status_string, fg='green')
            else:
                return click.style(hash_status_string, fg='red')

        def parse_ntp_offset(ntp_offset):
            if ntp_offset is None:
                return click.style('{:>15s}'.format("???"), fg='red')
            try:
                number_milli_seconds = float(ntp_offset)
                float_string = "{:>15f}".format(number_milli_seconds)
                if abs(number_milli_seconds) < 200:
                    return click.style(float_string, fg='green')
                else:
                    return click.style(float_string, fg='red')
            except ValueError as e:
                print(e)
                return click.style('{:>15s}'.format("???"), fg='red')

        node = dict(node)
        for k in ['ssh', 'swarm', 'ready', 'slave', 'ok']:
            if type(node.get(k)) is not str:
                node[k] = unbool(node.get(k))
        node["slave_faults_hash"] = compare_hash(local_hash_version, node.get("slave:faults"))
        node["slave_version"] = click.style("{:<14s}".format(str(node.get("slave:version")) or "???"))
        node['hostname'] = node.get('hostname') or "???"
        node['ntp'] = parse_ntp_offset(node.get("ntp", None))

        click.echo(FORMAT.format(**node))

    config = get_config({})
    local_path = config['faults_folder_local']
    remote_path = config['faults_folder_host']
    container_path = config['faults_folder_container']

    # Auxilliary function that sorts file list alphabetically and then
    # calculates md5sum of files contentent
    def md5(fname):
        hash_md5 = hashlib.md5()
        all_files = []
        for root, dirs, files in os.walk(fname, topdown=False):
            for name in files:
                file = os.path.join(root, name)
                all_files.append(file)
        all_files.sort()
        for file in all_files:
            with open(file, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        return hash_md5.hexdigest()

    local_hash_calculation = md5(local_path)

    status = ctx.obj['engine'].cluster_status(container_path)

    if status is None:
        click.echo("Cluster down, please run 'cluster up'")
        exit(-1)

    click.echo("Local Faults Folder ("+str(local_path)+") MD5: " + str(local_hash_calculation))
    click.echo('Cluster status:')
    print_header()
    for node in status:
        print_node(node, local_hash_calculation)

    OK = all(node['ok'] for node in status)

    swarm_nodes = ctx.obj['engine'].nodes()
    config_nodes = ctx.obj['config'].get('nodes', [])
    config_nodes = [n.get('address') for n in config_nodes]
    not_in_config = [n for n in swarm_nodes if n.ip not in config_nodes]

    if not_in_config:
        OK = False
        click.echo("")
        click.echo("Nodes in Swarm but not in config:")
        for node in not_in_config:
            node = {'address': node.ip,
                    'hostname': node.hostname}
            for k in ['ssh', 'swarm', 'ready', 'slave', 'slave:version', 'slave:faults', 'ntp', 'ok']:
                node[k] = "???"

            print_node(node, local_hash_calculation)

    click.echo("")
    if OK:
        click.echo("Cluster ready!")
    else:
        click.echo("Some errors found, please run 'cluster up'")
        exit(-1)


@cli.command('benchmark')
@click.option('--app', type=click.File('r'), required=True,
              help="App description file.")
@click.option('--churn', type=click.File('r'), required=False,
              help="Churn description file.")
@click.option('--runs', type=int, default=1,
              help="Number of benchmark runs.")
@click.option('--name', type=str, required=True,
              help="Benchmark name.")
@click.option('--run-time', type=int, required=False,
              help="Benchmark run duration.")
@click.option('--start-time', type=int, default=10,
              help="Waiting time at start of run.")
@click.option('--end-time', type=int, default=10,
              help="Waiting time at end of run.")
@click.option('--dry-run', is_flag=True,
              help="Dry run experiment.")
@click.pass_context
def benchmark(ctx, **kwargs):
    """Runs benchmarks."""
    ctx.obj.update(kwargs)

    ctx.obj['app'] = yaml.load(ctx.obj['app'])
    ctx.obj['churn_string'] = ""
    if ctx.obj['churn']:
        ctx.obj['churn_string'] = ctx.obj['churn'].read()
        ctx.obj['churn'].seek(0)
        ctx.obj['churn'] = yaml.load(ctx.obj['churn_string'])
        # ctx.obj['churn'] = yaml.load(ctx.obj['churn'])

    if not ctx.obj['churn'] and not ctx.obj['run_time']:
        raise click.UsageError(
            "Either --churn or --run-time must be specified")

    if ctx.obj['runs'] < 1:
        raise click.UsageError("--runs must be >= 1")

    bench = Benchmark(ctx.obj['engine'], ctx.obj['config'], ctx.obj['name'],
                      ctx.obj['app'], ctx.obj['churn'], ctx.obj['churn_string'],
                      ctx.obj['run_time'], ctx.obj['start_time'], ctx.obj['end_time'])

    if ctx.obj['dry_run']:
        bench.start(dry_run=True)
    else:
        for _ in range(ctx.obj['runs']):
            try:
                # if ctx.obj['config'].environment.sync_ntp
                #     ctx.obj['engine'].sync_clocks()
                _cluster_status(ctx)
                ctx.obj['engine'].start_ntp_sync()
                _cluster_status(ctx)
                bench.start(dry_run=False)
            except KeyboardInterrupt:
                click.echo("Cleaning up before exit...")
                bench.stop(wait=0, get_logs=False)
                exit(1)


@cli.command('get_logs')
@click.option('--remote-file-name', type=str, required=True,
              help="If a bug happens and you still need to recover logs")
@click.option('--local-folder', type=str, required=True,
              help="If a bug happens and you still need to recover logs")
@click.pass_context
def cluster_gather_logs(ctx, **kwargs):
    ctx.obj.update(kwargs)

    bench = Benchmark(ctx.obj['engine'],
                      ctx.obj['config'], "Name", "spec", run_time=123)
    # print(ctx.obj)
    bench.manual_get_logs(ctx.obj['local_folder'], ctx.obj['remote_file_name'])


@cli.command('process_logs')
@click.option('--directory', type=str, required=True,
              help="If a bug happens and you want to rerun process logs")
@click.option('--filename', type=str, required=True,
              help="Main logs file")
@click.pass_context
def process_logs_again(ctx, **kwargs):
    ctx.obj.update(kwargs)

    parser = Parser(ctx.obj['filename'])
    parser.process_file(ctx.obj['directory'])

@cli.command('get_processed_events')
@click.pass_context
def cluster_gather_logs(ctx, **kwargs):
    ctx.obj.update(kwargs)

    engine = ctx.obj['engine']
    print(engine.get_processed_events())




@cli.command('prune')
@click.pass_context
def prune(ctx, **kwargs):
    """Prune rogue services and networks."""
    ctx.obj.update(kwargs)
    ctx.obj['engine'].prune()


if __name__ == '__main__':
    cli(prog_name='lsds')
