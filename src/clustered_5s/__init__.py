#!/usr/bin/env python3
import os
from typing import TextIO
import subprocess
import shlex
import sys

import click
import yaml
import docker

from .schemas import injest_config, config_nodes_schema, config_node_schema
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


@main.command()
@_infile_option
@_composefile_option
def generate_compose(infile: TextIO, compose_file: TextIO):
    """Generate a compose file for use with `docker stack`"""
    config = injest_config(infile)
    nodes, swarm = satisfy_config(config, {})
    # click.echo(f"nodes {nodes}")
    yaml.dump(config, compose_file)
    return nodes, swarm


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
    node, swarm = satisfy_config(config, {})

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
    nodes, _ = satisfy_config(config, {})

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
@click.argument("node", type=str)
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
    node: str,
    rotate_worker_token,
    rotate_manager_token,
    rotate_manager_unlock_key,
):
    """wrapper for docker swarm update"""
    config = injest_config(infile)
    node, swarm = satisfy_config(config, {})

    d_client = docker.from_env()

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
    nodes, _ = satisfy_config(config, {})

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
