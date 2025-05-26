#!/usr/bin/env python3
import os
from typing import TextIO

import click
import yaml

from .schemas import injest_config
from .cantgetno import satisfy_config, tracked_features_schema

# TODO: https://click.palletsprojects.com/en/stable/shell-completion/


@click.group()
@click.version_option()
def main():
    pass


# TODO: automatic swarm state backup
# TODO: set node state


@main.command()
@click.option(
    "-f",
    "--file",
    "--infile",
    "infile",
    # prompt=True,
    default="clustered_5s.toml",
    type=click.File("rb"),
)
@click.option(
    "-o",
    "--outfile",
    # prompt=True,
    default=lambda: os.environ.get("COMPOSE_FILE", "compose.yaml").split(
        os.environ.get("COMPOSE_PATH_SEPARATOR", ":")
    )[0],
    type=click.File("w"),
)
# @click.option(
#    "-D",
#    "--working-dir",
#    "--workidir",
#    "workidir",
#    default=".",
#    envvar="",
#    type=click.Path(file_okay=False, dir_okay=True)
# )
def generate_compose(infile: TextIO, outfile: TextIO):
    """Generate a compose file for use with `docker stack`"""
    config = injest_config(infile)

    features: tracked_features_schema = {}
    nodes, swarm = satisfy_config(config, features)

    click.echo(f"nodes {nodes}")
    click.echo(f"swarm {swarm}")

    yaml.dump(config, outfile)


if __name__ == "__main__":
    main()
