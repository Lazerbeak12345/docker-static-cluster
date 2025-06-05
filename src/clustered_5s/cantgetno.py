import jq

from .schemas import (
    Config,
    ConfigJQPool,
    ConfigJQPools,
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
    #"stacks",
    # upstream
    "volumes",
    "networks",
    "services",
)



def satisfy_stacks(config: Config) -> ConfigStacks:
    return ConfigStacks.model_validate({})
    config_d = config.model_dump()
    stacks_d = config_d.get("stacks") or {}

    for category_name in list(filter(lambda x: x!="swarm", _categories)):
        category_d = config_d[category_name]
        if not category_d:
            continue
        for thing_name, thing_d in category_d.items():
            if thing_d and "stack" not in thing_d:
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


def satisfy_plugins(
    config: Config
) -> ConfigPlugins:
    return config.plugins or ConfigPlugins({})

import json

def satisfy_jq_pools(config: Config)->Config:
    #print(satisfy_jq_pools)
    config_d = config.model_dump()
    #print(f"config_d {json.dumps(config_d)}")
    if config.jq_pools:
        pools: ConfigJQPools = config.jq_pools
        for pool_name, pool in pools.items():
            #print(f"pool {pool_name} {pool}")
            if not isinstance(pool, ConfigJQPool):
                raise TypeError("pool wasn't right")
            pool_d = pool.model_dump()
            #print(f"pool_d {pool_d}")
            for category_name in _categories:
                if category_name not in pool_d or not pool_d[category_name]:
                    continue
                #print(f"pre jq {pool_d[category_name]}")
                program = jq.compile(
                    pool_d[category_name],
                    args={
                        "pool": pool_name,
                        "category_name": category_name,
                        "config": config_d,
                    },
                )
                #print(f"program {program}")
                results = program.input_value(config_d)
                #print(f"results {results}")
                result = results.first()
                #print(f"result {results}")
                for v_name, volume in result.items():
                    #print(f"post_jq {v_name} {volume}")
                    if category_name not in config_d:
                        config_d[category_name] = {}
                    config_d[category_name][v_name] = volume
                    #print(f"post_jq {json.dumps(config_d)}")
                    config = Config.model_validate(config_d)
                    config_d = config.model_dump()
    #print(volume)
    #print(config.model_dump_json())
    #assert False
    return config


def satisfy_config(
    config: Config
) -> tuple[Config, ConfigNodes, ConfigSwarm, ConfigPlugins, ConfigStacks]:
    config = satisfy_jq_pools(config)
    #print(config.model_dump_json())
    #assert False

    stacks = satisfy_stacks(config)
    nodes = satisfy_nodes(config)
    swarm = config.swarm
    plugins = satisfy_plugins(config)
    return config, nodes, swarm, plugins, stacks
