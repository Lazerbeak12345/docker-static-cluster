#!/usr/bin/env python3
import os
import sys
import tomllib
from typing import TextIO

import click
import schema
import yaml

from .schemas import config_schema
from .cantgetno import satisfy_config

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
    if infile.name[-5:] == ".toml":
        try:
            parsed_config = tomllib.load(infile)
        except tomllib.TOMLDecodeError as e:
            click.echo(f"parse error in config file {infile.name}\n{e}")
            sys.exit(1)
    elif infile.name[-5:] == ".yaml":
        # TODO: error handling
        parsed_config = yaml.load(infile, yaml.Loader)
    else:
        raise NotImplementedError(f"File format not supported for {infile.name}")
    try:
        config = config_schema.validate(parsed_config)
    except schema.SchemaError as e:
        click.echo(f"schema error in config file {infile.name}\n{e}")
        sys.exit(1)
    nodes = satisfy_config(config, {})
    yaml.dump(config, outfile)


if __name__ == "__main__":
    main()
