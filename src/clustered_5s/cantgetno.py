import jq

from .schemas import (
    Config,
    ConfigNodes,
    ConfigSwarm,
    ConfigPlugins,
    ConfigStacks,
)


_categories = (
    # mine
    "plugins",
    "swarm",
    "nodes",
    "stacks",
    # upstream
    "volumes",
    "networks",
    "services",
)



def satisfy_stacks(config: Config) -> ConfigStacks:
    config_d = config.model_dump()
    stacks_d = config_d.get("stacks") or {}
    for category_name in _categories:
        category_d = config_d[category_name]
        if not category_d:
            continue
        for thing_name, thing_d in category_d.items():
            if "stack" not in thing_d:
                continue
            stack_name = thing_d["stack"]
            if stack_name not in stacks_d:
                stacks_d[stack_name] = {}
            if category_name not in stacks_d[stack_name]:
                stacks_d[stack_name][category_name] = []
            if thing_name not in stacks_d[stack_name][category_name]:
                stacks_d[stack_name][category_name].append(thing_name)
    return ConfigStacks.model_validate(stacks_d)


def satisfy_nodes(
    config: Config
) -> ConfigNodes:
    return config.nodes or ConfigNodes({})


def satisfy_swarm(
    config: Config
) -> ConfigSwarm:
    return config.swarm or ConfigSwarm()

def satisfy_plugins(
    config: Config
) -> ConfigPlugins:
    return config.plugins or ConfigPlugins({})


def satisfy_jq_pools(config: Config)->Config:
    config_d = config.model_dump()
    if config.jq_pools:
        pools = config.jq_pools
        for pool_name, pool in pools.items():
            for category_name in _categories:
                if category_name not in pool:
                    continue
                for v_name, volume in (
                    jq.compile(
                        pool[category_name],
                        args={
                            "pool": pool_name,
                            "category_name": category_name,
                            "config": config,
                        },
                    )
                    .input_value(config)
                    .first()
                    .items()
                ):
                    if category_name not in config_d:
                        config_d[category_name] = {}
                    config_d[category_name][v_name] = volume
                    config = Config.model_validate(config_d)
    return config


def satisfy_config(
    config: Config
) -> tuple[ConfigNodes, ConfigSwarm, ConfigPlugins, ConfigStacks]:
    config = satisfy_jq_pools(config)

    stacks = satisfy_stacks(config)
    nodes = satisfy_nodes(config)
    swarm = satisfy_swarm(config)
    plugins = satisfy_plugins(config)
    return nodes, swarm, plugins, stacks
