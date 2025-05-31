#!/usr/bin/env python3
import os
from typing import TextIO
import json
import subprocess
import shlex
import sys

import click
import yaml
import docker

from .schemas import injest_config, config_schema
from .cantgetno import satisfy_config

# TODO: https://click.palletsprojects.com/en/stable/shell-completion/
# TODO: automatic swarm state backup


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
    default="clustered_5s.toml",
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
@_infile_option
@_composefile_option
def generate_compose(infile: TextIO, compose_file: TextIO):
    """Generate a compose file for use with `docker stack`"""
    config = injest_config(infile)
    nodes, swarm, plugins, stack = satisfy_config(config, {})
    yaml.dump(config, compose_file)
    return nodes, swarm, plugins, stack


@main.command()
@click.argument("output", type=click.File("w"))
def generate_compose_schema(output: TextIO):
    """Generate the schema file for the config"""
    json.dump(config_schema.json_schema(""), output)


@main.command()
@_infile_option
@_composefile_option
@_as_remote_node_option
@click.option("--skip-swarm", is_flag=True)
@click.option("--skip-plugins", is_flag=True)
@click.option("--skip-nodes", is_flag=True)
@click.option("--skip-propagate-config", is_flag=True)
@click.option("--skip-stack-deploy", is_flag=True)
@click.argument("stack_name", type=str)
@click.pass_context
def deploy(
    ctx,
    infile: TextIO,
    compose_file: TextIO,
    as_remote_node: str|None,
    skip_swarm: bool,
    skip_plugins: bool,
    skip_nodes: bool,
    skip_propagate_config: bool,
    skip_stack_deploy: bool,
    stack_name: str,
):
    """Deploy the config file."""
    node_settings, swarm_settings, plugin_settings, stack_settings = ctx.invoke(
        generate_compose,
        infile=infile,
        compose_file=compose_file,
    )

    if as_remote_node:
        d_client = docker.DockerClient(**node_settings[as_remote_node]["remote_docker_conf"])
    else:
        d_client = docker.from_env()

    if not skip_plugins:
        for plugin_name, plugin_config in plugin_settings.items():
            try:
                d_plugin = d_client.plugins.get(plugin_name)
                if plugin_config["remove"]:
                    d_plugin.remove(force=plugin_config["remove"] == "force")
                    continue
            except docker.errors.NotFound:
                d_plugin = d_client.plugins.install(
                    remote_name=plugin_config["image"],
                    local_name=plugin_name,
                )
            plugin_config["name"] = plugin_name
            d_plugin.configure(plugin_config)
        # TODO: prune option
    if not skip_swarm and swarm_settings:
        ctx.invoke(swarm_update)
    if not skip_nodes:
        for node_name in node_settings.keys():
            ctx.invoke(node_update, node=node_name)
        # TODO prune
    if not skip_propagate_config:
        for node_name in node_settings.keys():
            ctx.invoke(
                deploy,
                skip_plugins=False,
                skip_nodes=True,
                skip_swarm=True,
                skip_propagate_config=True,
                skip_stack_deploy=True,
                as_remote_node=node_name,
            )
    if not skip_stack_deploy:
        if as_remote_node:
            # TODO: support ssh
            click.echo("Stack commands cannot be run on a remote node")
            sys.exit(1)
        cmd = ["docker", "stack", "deploy"]

        cmd.append(stack_name)

        cmd.append("--compose-file")
        cmd.append(compose_file.name)

        # TODO prune

        click.echo(f"\n$ {shlex.join(cmd)}\n")
        subprocess.run(cmd)


# TODO: join swarm command
# TODO: new swarm command


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


@swarm.command("init")
@click.argument("node", type=str)
@_infile_option
@click.pass_context
@click.option("--force-new-cluster", is_flag=True)
def swarm_init(ctx, infile: TextIO, force_new_cluster: bool, node: str):
    """wrapper for docker swarm init"""
    config = injest_config(infile)
    node, swarm, _ = satisfy_config(config, {})

    d_client = docker.from_env()

    # TODO: remove unwanted keys
    click.echo(d_client.swarm.init(force_new_cluster=force_new_cluster, **swarm))

    ctx.invoke(swarm_join, node=node)


@swarm.command("join")
@click.argument("node", type=str)
@_infile_option
@click.option("--token", type=str)
def swarm_join(infile: TextIO, node: str, token):
    """wrapper for docker swarm join"""
    config = injest_config(infile)
    nodes, _, _ = satisfy_config(config, {})

    d_client = docker.from_env()

    the_node = nodes[node]
    if nodes:
        the_node["remote_addrs"] = [
            man_node["advertise_addr"]
            for man_node in nodes.values()
            if man_node["Role"] == "manager"
        ]

    # TODO: remove unwanted keys
    d_client.swarm.join(join_token=token, **the_node)


@swarm.command("update")
@_infile_option
@click.pass_context
@click.option("--force-new-cluster", is_flag=True)
@click.option("--rotate-worker-token", is_flag=True)
@click.option("--rotate-manager-token", is_flag=True)
@click.option("--rotate-manager-unlock-key", is_flag=True)
def swarm_update(
    ctx,
    infile: TextIO,
    force_new_cluster: bool,
    rotate_worker_token,
    rotate_manager_token,
    rotate_manager_unlock_key,
):
    """wrapper for docker swarm update"""
    config = injest_config(infile)
    node, swarm, _ = satisfy_config(config, {})

    d_client = docker.from_env()

    assert d_client.swarm.attrs, "Not connected to a swarm! You need to either init or join!"

    # TODO: remove unwanted keys
    d_client.swarm.update(
        force_new_cluster=force_new_cluster,
        rotate_worker_token=rotate_worker_token,
        rotate_manager_token=rotate_manager_token,
        rotate_manager_unlock_key=rotate_manager_unlock_key,
        **swarm,
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
@_infile_option
@click.argument("node", type=str)
@click.pass_context
def node_update(ctx, infile: TextIO, node):
    """wrapper for docker node update"""
    config = injest_config(infile)
    nodes, _, _ = satisfy_config(config, {})

    d_client = docker.from_env()
    d_node = d_client.nodes.get(node)

    rm = node not in nodes
    rm_force = False

    if not rm:
        node_spec = nodes[node]

        if "Role" in node_spec:
            role = node_spec["Role"]
            rm = role in ("rm-force", "rm")
            rm_force = role == "rm-force"
            node_spec["Role"] = "worker"
            node_spec["Availability"] = "drain"

        if not rm_force:
            del node_spec["listen_addr"]
            del node_spec["advertise_addr"]
            del node_spec["data_path_addr"]
            assert d_node.update(node_spec), "failed to update node"
            d_node.reload()
    if rm:
        assert d_node.remove(force=rm_force), "failed to remove node"


if __name__ == "__main__":
    main()
