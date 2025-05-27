import sys
from typing import TextIO
import tomllib

import click
from schema import Schema, Optional, Or, SchemaError
import yaml

jqlang_schema = Schema(str)

config_features_schema = Schema(
    {
        Optional("provides"): {str: bool},
        Optional("requires"): {str: bool},
    }
)

config_app_schema = {
    Optional("features"): {
        Optional("requires"): {str: bool},
    },
    # per-app unique configs
    Optional(str): object,
}

# TODO: create a matrix app config

config_volume_schema = Schema(
    {
        # our additions
        Optional("features"): config_features_schema,
        # upstream
        Optional(str): object,
    }
)

config_network_schema = Schema(
    {
        # our additions
        Optional("features"): config_features_schema,
        # upstream
        Optional(str): object,
    }
)

config_service_schema = Schema(
    {
        # our additions
        Optional("features"): config_features_schema,
        # upstream
        Optional(str): object,
    }
)

config_node_schema = Or(
    Schema(
        {
            # https://docs.docker.com/reference/cli/docker/node/rm/
            "role": "rm-force",
            Optional(str): object,
        }
    ),
    Schema(
        {
            "availability": "drain",
            # https://docs.docker.com/reference/cli/docker/node/rm/
            "role": Or(Schema("rm"), Schema("rm-demote")),
            Optional(str): object,
        }
    ),
    Schema(
        {
            # upstream (sorta)
            # https://docs.docker.com/reference/cli/docker/swarm/join/#options
            Optional("availability"): Or(
                Schema("active"),
                Schema("pause"),
                Schema("drain"),
                # TODO: default
            ),
            Optional("advertise-addr"): str,
            Optional("listen-addr"): str,
            Optional("data-path-addr"): str,
            Optional("data-path-port"): str,
            # https://docs.docker.com/reference/cli/docker/node/demote/
            # https://docs.docker.com/reference/cli/docker/node/promote/
            "role": Or(Schema("manager"), Schema("worker")),  # TODO: default
            # https://docs.docker.com/reference/cli/docker/node/update/
            # Optional("labels"): {str: str},
            # "id": str,
            # "hostname": str,
            # "platform": {
            #    # TODO: other osese
            #    # "os": Or(Schema("windows")),
            #    "os": str,
            #    # "arch": Or(Schema("x86_64"))
            #    "arch": str,
            # },
        }
    ),
)

config_nodes_schema = Schema({Optional(str): config_node_schema})

config_swarm_schema = Schema(
    {
        # https://docs.docker.com/reference/cli/docker/swarm/update/#options
        Optional("autolock"): bool,
        Optional("max-snapshots"): int,
        Optional("snapshot-interval"): int,
        Optional("task-history-limit"): int,
        # https://docs.docker.com/reference/cli/docker/swarm/ca/
        Optional("ca"): {
            Optional("cert"): str,
            Optional("key"): str,
            Optional("cert-expiry"): str,
            Optional("external-ca"): [str],
        },
        # https://docs.docker.com/reference/cli/docker/swarm/init/
        # TODO: Optional("autolock"): bool,
        Optional("default-addr-pool"): [str],
        Optional("default-addr-pool-mask-length"): int,
        Optional("dispatcher-heartbeat"): int,
    }
)

config_schema = Schema(
    {
        # our additions
        #  swarm mode settings (based on commands under docker swarm)
        Optional("swarm"): config_swarm_schema,
        #  A docker swarm mode node
        Optional("nodes"): config_nodes_schema,
        #  Logical applications
        Optional("apps"): {
            str: config_app_schema,
        },
        #  Use this for making swarms
        Optional("resource-pools"): {
            str: {
                Optional("features"): config_features_schema,
                # jqlang queries on the config file that get appended to each config
                Optional("volumes"): jqlang_schema,
                Optional("networks"): jqlang_schema,
                Optional("services"): jqlang_schema,
            }
        },
        # overridden
        Optional("volumes"): {str: config_volume_schema},
        Optional("networks"): {str: config_network_schema},
        Optional("services"): {str: config_service_schema},
        # upstream
        Optional(str): object,
    }
)


def injest_config(config_file: TextIO) -> config_schema:
    if config_file.name[-5:] == ".toml":
        try:
            parsed_config = tomllib.load(config_file)
        except tomllib.TOMLDecodeError as e:
            click.echo(f"parse error in config file {config_file.name}\n{e}")
            sys.exit(1)
    elif config_file.name[-5:] == ".yaml":
        # TODO: error handling
        parsed_config = yaml.load(config_file, yaml.Loader)
    else:
        raise NotImplementedError(f"File format not supported for {config_file.name}")
    try:
        config = config_schema.validate(parsed_config)
    except SchemaError as e:
        click.echo(f"schema error in config file {config_file.name}\n{e}")
        sys.exit(1)

    return config
