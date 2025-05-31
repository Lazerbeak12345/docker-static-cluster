
from schema import Schema
import jq

from .schemas import (
    config_schema,
    config_nodes_schema,
    config_swarm_schema,
    config_plugins_schema,
    config_stacks_schema,
)

"""if true, it's been provided, and if false it's been requested but not provided"""
tracked_features_schema = Schema({str: bool})




def satisfy_stacks(config: config_schema) -> config_stacks_schema:
    stacks = {}
    for category_name in ["volumes", "networks", "services"]:
        if category_name not in config:
            continue
        for thing_name, thing in config[category_name].items():
            stack_name = thing["stack"]
            if stack_name not in stacks:
                stacks[stack_name] = []
            stacks[stack_name].append(thing_name)
            del thing["stack"]
    return stacks


def satisfy_nodes(
    config: config_schema
) -> config_nodes_schema:
    if "nodes" in config:
        nodes = config["nodes"]
        del config["nodes"]
    else:
        nodes = {}
    return nodes


def satisfy_swarm(
    config: config_schema
) -> config_nodes_schema:
    if "swarm" in config:
        swarm = config["swarm"]
        del config["swarm"]
    else:
        swarm = {}
    return swarm

def satisfy_plugins(
    config: config_schema
) -> config_nodes_schema:
    if "plugins" in config:
        plugins = config["plugins"]
        del config["plugins"]
    else:
        plugins = {}
    return plugins


def satisfy_jq_pools(config: config_schema):
    if "jq-pools" in config:
        pools = config["jq-pools"]
        for pool_name, pool in pools.items():
            for category_name in ("volumes", "networks", "services"):
                if category_name in pool:
                    for v_name, volume in (
                        jq.compile(
                            pool[category_name],
                            args={
                                "pool": pool_name,
                                "is_volume": category_name == "volumes",
                                "is_network": category_name == "networks",
                                "is_service": category_name == "services",
                                "config": config,
                            },
                        )
                        .input_value(config)
                        .first()
                        .items()
                    ):
                        if category_name not in config:
                            config[category_name] = {}
                        config[category_name][v_name] = volume
        del config["jq-pools"]
    return config


def satisfy_config(
    config: config_schema
) -> tuple[config_nodes_schema, config_swarm_schema, config_plugins_schema, config_stacks_schema]:
    # TODO: remove the satisfy key from each of the things that have it, and add it into the stacks object.
    stacks = satisfy_stacks(config)
    # TODO: jq should be as early as possible, and it should re-validate after
    satisfy_jq_pools(config)
    nodes = satisfy_nodes(config)
    swarm = satisfy_swarm(config)
    plugins = satisfy_plugins(config)
    return nodes, swarm, plugins, stacks
