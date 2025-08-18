# SPDX-FileCopyrightText: 2025 2025
# SPDX-FileContributor: Nathan Fritzler
#
# SPDX-License-Identifier: MIT

import jq

from pathlib import Path
from typing import cast

from pydantic import FilePath
import yaml
from .schemas import (
    Config,
    ConfigNodes,
    ConfigStack,
    ConfigSwarm,
    ConfigPlugins,
)


def satisfy_config(
    config: Config, stack_name: str
) -> tuple[Config, ConfigNodes, ConfigSwarm, ConfigPlugins, ConfigStack]:
    stack_info = config.stacks[stack_name]
    stack = stack_info.stack
    if not isinstance(stack, ConfigStack):
        with stack.open() as stack_stream:
            # TODO: safe_load_all
            contents = yaml.safe_load(stack_stream)

            stack = ConfigStack.model_validate(contents)
            config.stacks[stack_name].stack = stack

    stack_ext = stack.dsc
    if stack_ext:
        jq_script = stack_ext.jq
        if isinstance(jq_script, str):
            contents = (
                jq.compile(
                    jq_script,
                    args={
                        "config": config.model_dump(),
                        "stack_name": stack_name,
                    },
                )
                .input_value(stack.model_dump())
                .first()
            )

            stack = ConfigStack.model_validate(contents)
            config.stacks[stack_name].stack = stack

    # stack = satisfy_jq_pools(config, stack_name)
    # config.stacks[stack_name] = stack

    nodes = config.swarm_nodes or ConfigNodes({})
    swarm = config.swarm_settings
    plugins = stack_info.plugins or ConfigPlugins({})

    return config, nodes, swarm, plugins, stack
