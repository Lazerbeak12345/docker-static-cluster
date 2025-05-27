#!/usr/bin/env python3
import os
from typing import TextIO
import subprocess
import shlex
import sys

import click
import yaml

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


@swarm.command("ca")
@_infile_option
@click.option("-d", "--detach", is_flag=True)
@click.option("-q", "--quiet", is_flag=True)
@click.option("--rotate", is_flag=True)
def swarm_ca(infile: TextIO, detach: bool, quiet: bool, rotate: bool):
    """wrapper for docker swarm ca"""
    config = injest_config(infile)
    _, swarm = satisfy_config(config, {})

    cmd = ["docker", "swarm", "ca"]

    if "ca" in swarm:
        ca = swarm["ca"]
        if "cert" in ca:
            cmd.append("--ca-cert")
            cmd.append(ca["cert"])
        if "key" in ca:
            cmd.append("--ca-key")
            cmd.append(ca["key"])
        if "cert-expiry" in ca:
            cmd.append("--ca-cert-expiry")
            cmd.append(ca["cert-expiry"])
        if "external-ca" in ca:
            cmd.append("--external-ca")
            cmd.append(ca["external-ca"])
    if detach:
        cmd.append("--detach")
    if quiet:
        cmd.append("--quiet")
    if rotate:
        cmd.append("--rotate")
        click.echo(
            "Telling docker to rotate the CA. Be sure to update the appropriate values in your config file, if needed."
        )

    click.echo(f"$ {shlex.join(cmd)}")
    subprocess.run(cmd)


def _select_nodes(nodes: config_nodes_schema, node_names: list[str]):
    selected_nodes = {}
    if len(node_names) == 0:
        node_names = list(nodes.keys())
    assert len(node_names) != 0, "No nodes were found!"
    for node_name in node_names:
        if node_name not in nodes:
            click.echo(
                f"the node name {node_name} was not in the config file's node list"
            )
            sys.exit(1)
        selected_nodes[node_name] = nodes[node_name]
    return selected_nodes


@swarm.command("init")
@_infile_option
@click.option("--node-name", "node_names", type=str, multiple=True, default=[])
@click.option("--force-new-cluster", is_flag=True)
def swarm_init(infile: TextIO, node_names: list[str], force_new_cluster: bool):
    """wrapper for docker swarm init"""
    config = injest_config(infile)
    nodes, swarm = satisfy_config(config, {})

    for node in _select_nodes(nodes, node_names).values():
        cmd = ["docker", "swarm", "init"]

        if "advertise-addr" in node:
            cmd.append("--advertise-addr")
            cmd.append(node["advertise-addr"])
        if "autolock" in swarm:
            cmd.append(f"--autolock={swarm['autolock']}")
        if "availability" in node:
            cmd.append(f"--availability={node['availability']}")
        if "ca" in swarm:
            ca = swarm["ca"]
            if "cert-expiry" in ca:
                cmd.append("--ca-cert-expiry")
                cmd.append(ca["cert-expiry"])
        if "data-path-addr" in node:
            cmd.append("--data-path-addr")
            cmd.append(node["data-path-addr"])
        if "data-path-port" in node:
            cmd.append(f"--data-path-port={node['data-path-port']}")
        if "default-addr-pool" in swarm:
            for addr in swarm["default-addr-pool"].values():
                cmd.append("--default-addr-pool")
                cmd.append(addr)
        if "default-addr-pool-mask-length" in swarm:
            cmd.append("--default-addr-pool-mask-length")
            cmd.append(swarm["default-addr-pool-mask-length"])
        if "dispatcher-heartbeat" in swarm:
            cmd.append("--dispatcher-heartbeat")
            cmd.append(swarm["dispatcher-heartbeat"])
        if "ca" in swarm:
            ca = swarm["ca"]
            if "external-ca" in ca:
                cmd.append("--external-ca")
                cmd.append(ca["external-ca"])
        if force_new_cluster:
            cmd.append("--force-new-cluster")
        if "listen-addr" in node:
            cmd.append("--listen-addr")
            cmd.append(node["listen-addr"])
        if "max-snapshots" in swarm:
            cmd.append("--max-snapshots")
            cmd.append(swarm["max-snapshots"])
        if "snapshot-interval" in swarm:
            cmd.append("--snapshot-interval")
            cmd.append(swarm["snapshot-interval"])
        if "task-history-limit" in swarm:
            cmd.append("--task-history-limit")
            cmd.append(swarm["task-history-limit"])

        click.echo(f"$ {shlex.join(cmd)}")
        subprocess.run(cmd)


@swarm.command("join")
@_infile_option
@click.option("--node-name", "node_names", type=str, multiple=True, default=[])
@click.option("--token", type=str)
def swarm_join(infile: TextIO, node_names: list[str], token):
    """wrapper for docker swarm join"""
    config = injest_config(infile)
    nodes, _ = satisfy_config(config, {})

    for node in _select_nodes(nodes, node_names).values():
        cmd = ["docker", "swarm", "join"]

        if "advertise-addr" in node:
            cmd.append("--advertise-addr")
            cmd.append(node["advertise-addr"])
        if "availability" in node:
            cmd.append(f"--availability={node['availability']}")
        if "data-path-addr" in node:
            cmd.append("--data-path-addr")
            cmd.append(node["data-path-addr"])
        if "listen-addr" in node:
            cmd.append("--listen-addr")
            cmd.append(node["listen-addr"])
        if token:
            cmd.append("--token")
            cmd.append(token)

        click.echo(f"$ {shlex.join(cmd)}")
        subprocess.run(cmd)


@swarm.command("update")
@_infile_option
def swarm_update(infile: TextIO):
    """wrapper for docker swarm update"""
    config = injest_config(infile)
    _, swarm = satisfy_config(config, {})

    cmd = ["docker", "swarm", "join"]

    if "autolock" in swarm:
        cmd.append(f"--autolock={swarm['autolock']}")
    if "ca" in swarm:
        ca = swarm["ca"]
        if "cert-expiry" in ca:
            cmd.append("--ca-cert-expiry")
            cmd.append(ca["cert-expiry"])
    if "dispatcher-heartbeat" in swarm:
        cmd.append("--dispatcher-heartbeat")
        cmd.append(swarm["dispatcher-heartbeat"])
    if "ca" in swarm:
        ca = swarm["ca"]
        if "external-ca" in ca:
            cmd.append("--external-ca")
            cmd.append(ca["external-ca"])
    if "max-snapshots" in swarm:
        cmd.append("--max-snapshots")
        cmd.append(swarm["max-snapshots"])
    if "snapshot-interval" in swarm:
        cmd.append("--snapshot-interval")
        cmd.append(swarm["snapshot-interval"])
    if "task-history-limit" in swarm:
        cmd.append("--task-history-limit")
        cmd.append(swarm["task-history-limit"])

    click.echo(f"$ {shlex.join(cmd)}")
    subprocess.run(cmd)


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
    """
    pass


@node.command("rm")
@_infile_option
@click.argument("node", type=str)
def node_rm(infile: TextIO, node):
    """wrapper for docker node rm"""
    config = injest_config(infile)
    nodes, swarm = satisfy_config(config, {})

    for node in _select_nodes(nodes, [node]).values():
        cmd = ["docker", "node", "rm"]

        raise NotImplementedError(node_rm)

        click.echo(f"$ {shlex.join(cmd)}")
        subprocess.run(cmd)


@node.command("update")
@_infile_option
@click.argument("node", type=str)
@click.pass_context
def node_update(ctx, infile: TextIO, node):
    """wrapper for docker node update"""
    config = injest_config(infile)
    nodes, swarm = satisfy_config(config, {})

    for node_name, node in _select_nodes(nodes, [node]).items():
        cmd = ["docker", "node", "update"]

        if "availability" in node:
            cmd.append(f"--availability={node['availability']}")
        if "role" in node:
            cmd.append("--role")
            role = node["role"]
            if role in ("rm-force", "rm", "rm-demote"):
                ctx.invoke(node_rm, node=node_name)
                continue
            else:
                cmd.append(role)
        # TODO: find list of labels currently on node, take the diff.

        click.echo(f"$ {shlex.join(cmd)}")
        subprocess.run(cmd)


if __name__ == "__main__":
    main()
