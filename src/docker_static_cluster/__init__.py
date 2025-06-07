#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 2025
# SPDX-FileContributor: Nathan Fritzler
#
# SPDX-License-Identifier: MIT

import os
from typing import Dict, List, TextIO, Optional
import json
import subprocess
import shlex
import sys
import traceback

import click
import yaml
import docker
import docker.errors

from .schemas import (
    ConfigNode,
    ConfigNodeRMSpec,
    ConfigNodeSpec,
    ConfigNodes,
    ConfigPlugins,
    ConfigStack,
    ConfigSwarm,
    injest_config,
    Config,
)
from .cantgetno import satisfy_config

debug = True

# TODO: https://click.palletsprojects.com/en/stable/shell-completion/
# TODO: automatic swarm state backup


def run_cmd(args: List[str], **kwargs):
    click.echo(f"\n$ {shlex.join(args)}\n")
    # TODO: exit on subprocess errors, by default
    return subprocess.run(args, **kwargs)


@click.group()
@click.version_option()
def main():
    pass


_infile_option = click.option(
    "-f",
    "--file",
    "--infile",
    "infile",
    # prompt=True,
    default="docker_static_cluster.toml",
    type=click.File("rb"),
)

_composefile_option = click.option(
    "-c",
    "--compose-file",
    "compose_file",
    # prompt=True,
    default=lambda: os.environ.get("COMPOSE_FILE", "compose.yaml").split(
        os.environ.get("COMPOSE_PATH_SEPARATOR", ":")
    )[0],
    type=click.File("w"),
)

_as_remote_node_option = click.option(
    "-r",
    "--as-remote-node",
    "as_remote_node",
    type=str,
)


@main.command()
@click.argument("stack_name", type=str)
@_infile_option
@_composefile_option
def generate_compose(
    stack_name: str, infile: TextIO, compose_file: TextIO
) -> tuple[Config, ConfigNodes, ConfigSwarm, ConfigPlugins, ConfigStack]:
    """Generate a compose file for use with `docker stack`"""
    config = injest_config(infile)
    config, nodes, swarm, plugins, stack = satisfy_config(config, stack_name)
    stack_d = stack.model_dump()
    for key in ("jq_pools",):
        stack_d.pop(key)
    yaml.dump(stack_d, compose_file)
    return config, nodes, swarm, plugins, stack


@main.command()
@click.argument("output", type=click.File("w"))
def generate_compose_schema(output: TextIO):
    """Generate the schema file for the config"""
    json.dump(Config.model_json_schema(), output)


@main.command()
@_infile_option
@_composefile_option
@_as_remote_node_option
@click.option("--skip-swarm", is_flag=True)
@click.option("--skip-plugins", is_flag=True)
@click.option("--skip-nodes", is_flag=True)
@click.option("--skip-propagate-config", is_flag=True)
@click.option("--skip-stack-deploy", is_flag=True)
@click.option("--force-service-update", is_flag=True)
@click.argument("stack_name", type=str)
@click.pass_context
def deploy(
    ctx,
    infile: TextIO,
    compose_file: TextIO,
    as_remote_node: Optional[str],
    skip_swarm: bool,
    skip_plugins: bool,
    skip_nodes: bool,
    skip_propagate_config: bool,
    skip_stack_deploy: bool,
    force_service_update: bool,
    stack_name: str,
):
    """Deploy the config file."""
    _, nodes_settings, swarm_settings, plugins_settings, _ = ctx.invoke(
        generate_compose,
        stack_name=stack_name,
        infile=infile,
        compose_file=compose_file,
    )
    assert isinstance(nodes_settings, ConfigNodes)
    assert isinstance(swarm_settings, ConfigSwarm)
    assert isinstance(plugins_settings, ConfigPlugins)

    # TODO: something was ignoring unsupported "restart" option

    if as_remote_node:
        node_settings = nodes_settings[as_remote_node]
        assert node_settings, f"remote node {as_remote_node} could not be found"
        assert node_settings.remote_docker_conf, (
            f"remote node {as_remote_node} does not have a remote remote_docker_conf"
        )
        remote_docker_conf_d = node_settings.remote_docker_conf.model_dump()
        d_client = docker.DockerClient(
            **{
                key: value
                for key, value in remote_docker_conf_d.items()
                if value is not None
            }
        )
    else:
        d_client = docker.from_env()

    if not skip_plugins:
        for plugin_name, plugin_config in plugins_settings.items():
            try:
                d_plugin = d_client.plugins.get(plugin_name)
                if plugin_config.remove:
                    d_plugin.remove(force=plugin_config.remove == "force")
                    continue
            except docker.errors.NotFound:
                d_plugin = d_client.plugins.install(
                    remote_name=plugin_config.image,
                    local_name=plugin_name,
                )
            plugin_config_d = plugin_config.model_dump()
            plugin_config_d["name"] = plugin_name
            d_plugin.configure(plugin_config)
        # TODO: prune option
    if not skip_swarm and swarm_settings:
        ctx.invoke(swarm_update, stack_name=stack_name)
    if not skip_nodes:
        for node_name in nodes_settings.keys():
            ctx.invoke(node_update, node=node_name, stack_name=stack_name)
        # TODO prune
    if (not skip_propagate_config) and (not skip_plugins):
        for node_name in nodes_settings.keys():
            ctx.invoke(
                deploy,
                skip_plugins=False,
                skip_nodes=True,
                skip_swarm=True,
                skip_propagate_config=True,
                skip_stack_deploy=True,
                as_remote_node=node_name,
                stack_name=stack_name,
            )
    if not skip_stack_deploy:
        # TODO prune

        # stack_settings = stacks_settings[stack_name]
        if as_remote_node:
            # TODO: support ssh
            raise NotImplementedError("Stack commands cannot be run on a remote node")
        # NOTE: below doesn't do things the right way
        #
        # cmd = ["docker"]
        #
        # this instead adds behavior expected from docker stack,
        #  alike that of docker compose
        # TODO: this is python code, but they don't provide a python API
        cmd = ["docker-sdp"]

        cmd.extend(["stack", "deploy"])
        cmd.append(stack_name)
        cmd.extend(["--compose-file", compose_file.name])

        run_cmd(cmd)
    if force_service_update:
        if as_remote_node:
            # TODO: support ssh
            raise NotImplementedError(
                "forcing a service update cannot be run on a remote node"
            )

        cmd = ["docker", "stack", "services", "-q", stack_name]
        result = run_cmd(cmd, capture_output=True, text=True)
        service_ids: List[str] = result.stdout.splitlines()

        click.echo("\n".join(service_ids))

        for service_id in service_ids:
            cmd = ["docker", "service", "update"]
            cmd.append("--force")
            cmd.append(service_id)

            run_cmd(cmd)


# TODO: make these into commands
#
# TIP: if you're looking for a way to force-restart stuff,
#
#     docker stack services -q $stack | xargs -rt -n1 -- docker service update --force
#
# from https://stackoverflow.com/a/71724439/6353323
#
# can recreate everything
#
#     docker service update --force $service
#
# from https://stackoverflow.com/a/44110795/6353323
#
# will just update the unchanged

# TODO: join swarm command


@main.group()
def swarm():
    """
    wrapper for docker swarm

    Not needed:
    - join-token
    - leave
    - unlock
    - unlock-key
    """
    pass


_swarm_init_keys = (
    "task_history_retention_limit",
    "snapshot_interval",
    "keep_old_snapshots",
    "log_entries_for_slow_followers",
    "heartbeat_tick",
    "dispatcher_heartbeat_period",
    "signing_ca_cert",
    "signing_ca_key",
)


@swarm.command("init")
# @click.argument("node", type=str)
@click.argument("stack_name", type=str)
@_infile_option
# @click.pass_context
@click.option("--force-new-cluster", is_flag=True)
def swarm_init(
    infile: TextIO,
    stack_name: str,
    force_new_cluster: bool,  # , node: str
):
    """wrapper for docker swarm init"""
    config = injest_config(infile)
    config, _, swarm_settings, _, _ = satisfy_config(config, stack_name)

    d_client = docker.from_env()

    kwargs = {}

    swarm_settings_d = swarm_settings.model_dump()

    for key in _swarm_init_keys:
        if key in swarm_settings_d:
            kwargs[key] = swarm_settings_d[key]

    click.echo(d_client.swarm.init(force_new_cluster=force_new_cluster, **kwargs))

    # ctx.invoke(swarm_join, node=node, stack_name=stack_name)


main.add_command(swarm_init)


# BUG: this command wasn't working, so I've disabled it.
# @swarm.command("join")
@click.argument("node", type=str)
@click.argument("stack_name", type=str)
@_infile_option
@click.option("--token", type=str)
def swarm_join(stack_name: str, infile: TextIO, node: str, token):
    """wrapper for docker swarm join"""
    config = injest_config(infile)
    config, nodes, _, _, _ = satisfy_config(config, stack_name)

    d_client = docker.from_env()

    the_node = nodes[node]

    kwargs: Dict[str, object] = {}

    kwargs["remote_addrs"] = [
        man_node.Status.Addr
        for node_name, man_node in nodes.items()
        if isinstance(man_node, ConfigNode)
        and node_name != node
        and man_node.Status
        and man_node.Status.Addr
    ]

    if the_node.Status and the_node.Status.Addr:
        kwargs["advertise_addr"] = the_node.Status.Addr
    if the_node.ManagerStatus and the_node.ManagerStatus.Addr:
        kwargs["listen_addr"] = the_node.ManagerStatus.Addr
    if the_node.DataPathAddr:
        kwargs["data_path_addr"] = the_node.DataPathAddr

    click.echo(json.dumps(kwargs))

    assert d_client.swarm.join(join_token=token, **kwargs)


# BUG: I've disabled this command, see above
# main.add_command(swarm_join)


@swarm.command("update")
@click.argument("stack_name", type=str)
@_infile_option
@click.option("--rotate-worker-token", is_flag=True)
@click.option("--rotate-manager-token", is_flag=True)
@click.option("--rotate-manager-unlock-key", is_flag=True)
def swarm_update(
    stack_name: str,
    infile: TextIO,
    rotate_worker_token,
    rotate_manager_token,
    rotate_manager_unlock_key,
):
    """wrapper for docker swarm update"""
    config = injest_config(infile)
    config, _, swarm_settings, _, _ = satisfy_config(config, stack_name)

    d_client = docker.from_env()

    assert d_client.swarm.attrs, (
        "Not connected to a swarm! You need to either init or join!"
    )

    kwargs = {}

    swarm_settings_d = swarm_settings.model_dump()

    for key in _swarm_init_keys:
        if key in swarm_settings_d:
            kwargs[key] = swarm_settings_d[key]

    d_client.swarm.update(
        rotate_worker_token=rotate_worker_token,
        rotate_manager_token=rotate_manager_token,
        rotate_manager_unlock_key=rotate_manager_unlock_key,
        **kwargs,
    )


@main.group()
def node():
    """
    wrapper for docker node

    Not needed:
    - demote
    - inspect
    - ls
    - promote
    - ps
    - rm
    """
    pass


@node.command("update")
@click.argument("stack_name", type=str)
@_infile_option
@click.argument("node", type=str)
def node_update(stack_name: str, infile: TextIO, node):
    """wrapper for docker node update"""
    config = injest_config(infile)
    config, nodes, _, _, _ = satisfy_config(config, stack_name)

    rm = node not in nodes
    rm_force = False

    d_client = docker.from_env()
    try:
        d_node = d_client.nodes.get(node)
    except docker.errors.APIError as e:
        if e.status_code == 404:
            if rm:
                click.echo(f"node {node} was already removed")
                return
            else:
                click.echo(f"node {node} needs to join the swarm")
                # TODO: do this automatically
                raise NotImplementedError(f"can't yet auto-join node {node}") from e
        else:
            raise e

    if not rm:
        node_settings: ConfigNode = nodes[node]

        spec = node_settings.Spec

        if isinstance(spec, ConfigNodeRMSpec):
            rm = True
            rm_force = spec.Role == "rm-force"

            node_settings.Spec = ConfigNodeSpec(Role="worker", Availability="drain")

        if not rm_force:
            # TODO: may need to actually promote or demote
            assert d_node.update(node_settings.Spec.model_dump()), (
                "failed to update node"
            )
            d_node.reload()
    if rm:
        assert d_node.remove(force=rm_force), "failed to remove node"


def handle_ecxeption(exc_type, exc_value, exc_traceback):
    try:
        raise exc_value
    except docker.errors.APIError as e:
        # TODO: put this to stderr
        click.echo(f"APIError {type(e).__name__}")
        if debug:
            click.echo(traceback.format_exc())
            click.echo()
        click.echo(
            json.dumps(
                {
                    "is_client_error": e.is_client_error(),
                    "is_error": e.is_error(),
                    "is_server_error": e.is_server_error(),
                    "status_code": e.status_code,
                    "strerror": e.strerror,
                    "errno": e.errno,
                    "filename": e.filename,
                    "filename2": e.filename2,
                }
            )
        )
        click.echo()
        click.echo(e)
    except docker.errors.DockerException as e:
        """ Base class for docker-py exc. """
        # TODO: put this to stderr
        click.echo("DockerException")
        click.echo(e)


sys.excepthook = handle_ecxeption
