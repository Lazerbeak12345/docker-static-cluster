#!/usr/bin/env python3
import os
import sys
import tomllib

import click
import schema

# TODO: https://click.palletsprojects.com/en/stable/shell-completion/


@click.group()
@click.version_option()
def main():
    pass


config_schema = schema.Schema(
    {
        "clustered_5s_config_version": "0.0.0",
    }
)


@main.command()
@click.option(
    "-f",
    "--file",
    "--infile",
    "infile",
    #prompt=True,
    default="clustered_5s.toml",
    type=click.File("rb"),
)
@click.option(
    "-o",
    "--outfile",
    #prompt=True,
    default=lambda: os.environ.get("COMPOSE_FILE", "compose.yaml").split(
        os.environ.get("COMPOSE_PATH_SEPARATOR", ":")
    )[0],
    type=click.File("w"),
)
def generate_compose(infile, outfile):
    """Generate a compose file for use with `docker stack`"""
    try:
        config = config_schema.validate(tomllib.load(infile))
    except schema.SchemaError as e:
        click.echo(f"error in config file {infile.name}\n{e}")
        sys.exit(1)
    click.echo(config)
    raise NotImplementedError(generate_compose)


if __name__ == "__main__":
    main()
