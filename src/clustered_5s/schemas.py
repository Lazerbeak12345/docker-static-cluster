import sys
from typing import TextIO
import tomllib

import click
from schema import Schema, Optional, Or, SchemaError
import yaml

jqlang_schema = Schema(str)


# TODO: create a matrix app config

config_volume_schema = Schema(
    {
        # our additions
        "stack": str,
        # upstream
        Optional(str): object,
    }
)

config_network_schema = Schema(
    {
        # our additions
        "stack": str,
        # upstream
        Optional(str): object,
    }
)

config_service_schema = Schema(
    {
        # our additions
        "stack": str,
        # upstream
        Optional(str): object,
    }
)

config_node_schema = Or(
    Schema(
        {
            # https://docs.docker.com/reference/cli/docker/node/rm/
            Optional(str): object,
            "Spec": {
                "Role": Or(Schema("rm"), Schema("rm-force")),
                Optional(str): object,
            }
        }
    ),
    Schema(
        {
            # my addons
            Optional("remote_docker_conf"): {
                "base_url": str,
                Optional("version"): str,
                Optional("timeout"): str,
                Optional("tls"): Or(object, bool),
                Optional("user_agent"): str,
                Optional("credstore_env"): dict,
                Optional("use_ssh_client"): bool,
                Optional("max_pool_size"): int,
            },
            # upstream (sorta)
            # https://docs.docker.com/reference/cli/docker/node/demote/
            # https://docs.docker.com/reference/cli/docker/node/promote/
            # https://docs.docker.com/reference/cli/docker/node/update/
            # https://docker-py.readthedocs.io/en/stable/nodes.html
            # https://docker-py.readthedocs.io/en/stable/swarm.html?highlight=join#docker.models.swarm.Swarm.join
            # upstream Swarm.join
            Optional("DataPathAddr"): str,
            Optional("ManagerStatus"): {
                Optional("Addr"): str, # listen_addr
                Optional(str): object,
            },
            # upstream Node.attrs
            "Spec": {
                "Availability": Or(Schema("active"), Schema('pause'), Schema('drain')),
                "Role": Or(Schema("manager"), Schema("worker")),
                Optional("Labels"): {str: object},
                Optional(str): object,
            },
            Optional("Status"): {
                Optional("Addr"): str, # advertise_addr
                Optional(str): object,
            },
            Optional(str): object,
        }
    ),
)

config_nodes_schema = Schema({Optional(str): config_node_schema})

config_swarm_schema = Schema(
    {
        # https://docker-py.readthedocs.io/en/stable/swarm.html#docker.models.swarm.Swarm.init
        Optional("advertise_addr"): str,
        Optional("listen_addr"): str,
        Optional("default_addr_pool"): [str],
        Optional("subnet_size"): int,
        Optional("data_path_addr"): str,
        Optional("data_path_port"): int,
        Optional("task_history_retention_limit"): int,
        Optional("snapshot_interval"): int,
        Optional("keep_old_snapshots"): int,
        Optional("log_entries_for_slow_followers"): int,
        Optional("heartbeat_tick"): int,
        Optional("election_tick"): int,
        Optional("dispatcher_heartbeat_period"): int,
        Optional("node_cert_expiry"): int,
        # this CA stuff is likely broken. all of the cert
        Optional("external_ca"): {
            "url": str,
            "protocol": str,
            "options": dict,
            Optional("ca_cert"): str,
        },
        Optional("name"): str,
        Optional("labels"): {str: str},
        Optional("signing_ca_cert"): str,
        Optional("signing_ca_key"): str,
        Optional("ca_force_rotate"): int,
        Optional("autolock_managers"): bool,
        Optional("log_driver"): {"name": str, Optional("options"): dict},
    }
)

config_plugins_schema = Schema(
    {
        str: {
            "image": str,
            "settings": dict,
            Optional("enabled"): bool,
            Optional("remove"): Or(Schema("force"), bool),
        }
    }
)

config_stacks_schema = Schema({})

config_schema = Schema(
    {
        # our additions
        #  Docker plugin settings
        Optional("plugins"): config_plugins_schema,
        #  swarm mode settings (based on commands under docker swarm)
        Optional("swarm"): config_swarm_schema,
        #  A docker swarm mode node
        Optional("nodes"): config_nodes_schema,
        #  Corresponds to docker stack ls
        Optional("stacks"): { str: config_stacks_schema },
        #  Use this for making swarms
        Optional("jq-pools"): {
            str: {
                # jqlang queries on the config file that get appended to each config
                Optional(Or(
                    # mine
                    Schema("plugins"),
                    Schema("swarm"),
                    Schema("nodes"),
                    Schema("stacks"),
                    # upstream
                    Schema("volumes"),
                    Schema("networks"),
                    Schema("services"),
                )): jqlang_schema,
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
