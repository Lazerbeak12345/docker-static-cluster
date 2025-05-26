import click
from schema import Schema
from .schemas import config_schema, config_nodes_schema, config_features_schema

"""if true, it's been provided, and if false it's been requested but not provided"""
tracked_features_schema = Schema({str: bool})


def feature_requests(found: config_features_schema, so_far: tracked_features_schema):
    """Given the feature schema, include requests in tracked"""
    if "requires" in found:
        requires = found["requires"]
        for key, value in requires.items():
            if value and (key not in so_far):
                so_far[key] = False
        del found["requires"]
    click.echo(f"so_far {so_far}")


def satisfy_apps(config: config_schema, features: tracked_features_schema):
    """
    Find the apps in the config,
    evaluate builtin's defaults and apply user overrides
    take resulting active feature requests and add them to the list
    """
    if "apps" in config:
        apps = config["apps"]
        # TODO: evaluate builtin's defaults

        for name, app in apps.items():
            if "features" in app:
                feature_requests(app["features"], features)
        del config["apps"]
    return config


def satisfy_nodes(
    config: config_schema, features: tracked_features_schema
) -> config_nodes_schema:
    if "nodes" in config:
        nodes = config.nodes
        raise NotImplementedError(satisfy_nodes)
    else:
        nodes = {}
    click.echo(f"config {config}")
    return config, nodes


def satisfy_resource_pools(config: config_schema, features: tracked_features_schema):
    if "resource-pools" in config:
        raise NotImplementedError(satisfy_resource_pools)
    return config


def satisfy_config(
    config: config_schema, features: tracked_features_schema
) -> config_nodes_schema:
    satisfy_apps(config, features)
    satisfy_resource_pools(config, features)
    nodes = satisfy_nodes(config, features)
    return nodes
