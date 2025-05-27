import sys

import click
from schema import Schema
import jq

from .schemas import (
    config_schema,
    config_nodes_schema,
    config_features_schema,
    config_swarm_schema,
)

"""if true, it's been provided, and if false it's been requested but not provided"""
tracked_features_schema = Schema({str: bool})


def feature_requires(found: config_features_schema, so_far: tracked_features_schema):
    """Given the feature schema, include requests in tracked"""
    if "requires" in found:
        requires = found["requires"]
        for key, value in requires.items():
            if value and (key not in so_far):
                so_far[key] = False
        del found["requires"]


def feature_provides(found: config_features_schema, so_far: tracked_features_schema):
    """Given the feature schema, mark features as provided"""
    if "provides" in found:
        provides = found["provides"]
        for key, value in provides.items():
            if value:
                so_far[key] = True
        del found["provides"]


def satisfy_apps(config: config_schema, features: tracked_features_schema):
    """
    Find the apps in the config,
    evaluate builtin's defaults and apply user overrides
    take resulting active feature requests and add them to the list
    """
    if "apps" in config:
        apps = config["apps"]
        # TODO: evaluate builtin's defaults

        for app in apps.values():
            if "features" in app:
                feature_requires(app["features"], features)
        del config["apps"]
    return config


def satisfy_nodes(
    config: config_schema, features: tracked_features_schema
) -> config_nodes_schema:
    if "nodes" in config:
        nodes = config["nodes"]
        del config["nodes"]
    else:
        nodes = {}
    return nodes


def satisfy_swarm(
    config: config_schema, features: tracked_features_schema
) -> config_nodes_schema:
    if "swarm" in config:
        swarm = config["swarm"]
        del config["swarm"]
    else:
        swarm = {}
    return swarm


def satisfy_resource_pools(config: config_schema, features: tracked_features_schema):
    if "resource-pools" in config:
        pools = config["resource-pools"]

        # TODO: evaluate builtin's defaults

        for pool_name, pool in pools.items():
            if "features" in pool:
                feature_requires(pool["features"], features)
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
                            },
                        )
                        .input_value(config)
                        .first()
                        .items()
                    ):
                        config[category_name][v_name] = volume
            if "features" in pool:
                feature_provides(pool["features"], features)
        del config["resource-pools"]
    return config


def satisfy_config(
    config: config_schema, features: tracked_features_schema
) -> tuple[config_nodes_schema, config_swarm_schema]:
    satisfy_apps(config, features)
    satisfy_resource_pools(config, features)
    nodes = satisfy_nodes(config, features)
    swarm = satisfy_swarm(config, features)
    for feature, resolved in features.items():
        if not resolved:
            # TODO: this isn't a very good error message
            click.echo(f"the feature {feature} was required, but not resolved")
            sys.exit(1)
    return nodes, swarm
