# SPDX-FileCopyrightText: 2025 2025
# SPDX-FileContributor: Nathan Fritzler
#
# SPDX-License-Identifier: MIT

import jq

from .schemas import (
    Config,
    ConfigJQPool,
    ConfigJQPools,
    ConfigNodes,
    ConfigStack,
    ConfigSwarm,
    ConfigPlugins,
)


_categories = (
    # mine
    "plugins",
    "swarm",
    "nodes",
    # "stacks",
    # upstream
    "volumes",
    "networks",
    "services",
)


def satisfy_jq_pools(config: Config, stack_name: str) -> ConfigStack:
    assert isinstance(stack_name, str), type(stack_name)
    stack = config.stacks[stack_name]
    if stack.jq_pools:
        pools: ConfigJQPools = stack.jq_pools
        for pool_name, pool in pools.items():
            if not isinstance(pool, ConfigJQPool):
                raise TypeError("pool wasn't right")
            pool_d = pool.model_dump()
            for category_name in _categories:
                if category_name not in pool_d or not pool_d[category_name]:
                    continue
                stack_d = stack.model_dump()
                if category_name not in stack_d:
                    stack_d[category_name] = {}
                config_d = config.model_dump()
                program = jq.compile(
                    pool_d[category_name],
                    args={
                        "pool": pool_name,
                        "config": config_d,
                        "stack": stack_d,
                    },
                )
                results = program.input_value(config_d)
                result = results.first()
                for v_name, volume in result.items():
                    stack_d[category_name][v_name] = volume
                    stack = ConfigStack.model_validate(stack_d)
    return stack


def satisfy_config(
    config: Config, stack_name: str
) -> tuple[Config, ConfigNodes, ConfigSwarm, ConfigPlugins, ConfigStack]:
    stack = satisfy_jq_pools(config, stack_name)
    config.stacks[stack_name] = stack

    nodes = config.nodes or ConfigNodes({})
    swarm = config.swarm
    plugins = config.plugins or ConfigPlugins({})
    return config, nodes, swarm, plugins, stack
