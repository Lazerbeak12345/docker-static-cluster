# SPDX-FileCopyrightText: 2025 2025
# SPDX-FileContributor: Nathan Fritzler
#
# SPDX-License-Identifier: MIT

import sys
from typing import (
    ItemsView,
    Iterator,
    KeysView,
    Literal,
    Union,
    Dict,
    Any,
    ValuesView,
    Optional,
    Generic,
    TypeVar,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import click
import yaml
from pydantic import BaseModel, ConfigDict, RootModel, ValidationError

jqlang_schema = str


# TODO: ensure added fields get removed before compose file dump
# TODO: default values (which must be unique instances for each container instance)

# TODO: create a matrix app config

K = TypeVar("K")
V = TypeVar("V")


class DictLikeMixin(Generic[K, V]):
    root: Dict[K, V]

    def __getitem__(self, key: K) -> V:
        return self.root[key]

    def __setitem__(self, key: K, value: V) -> None:
        self.root[key] = value

    def __delitem__(self, key: K) -> None:
        del self.root[key]

    def __iter__(self) -> Iterator[K]:
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def keys(self) -> KeysView[K]:
        return self.root.keys()

    def items(self) -> ItemsView[K, V]:
        return self.root.items()

    def values(self) -> ValuesView[V]:
        return self.root.values()

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        return self.root.get(key, default)


class ConfigVolume(BaseModel):
    # our additions
    # stack: Optional[str] = None
    # upstream
    model_config = ConfigDict(extra="allow")


class ConfigVolumes(
    DictLikeMixin[str, ConfigVolume], RootModel[Dict[str, ConfigVolume]]
):
    pass


class ConfigNetwork(BaseModel):
    # our additions
    # stack: Optional[str] = None
    # upstream
    model_config = ConfigDict(extra="allow")


class ConfigNetworks(
    DictLikeMixin[str, ConfigNetwork], RootModel[Dict[str, ConfigNetwork]]
):
    pass


class ConfigService(BaseModel):
    # our additions
    # stack: Optional[str] = None
    # upstream
    model_config = ConfigDict(extra="allow")


class ConfigServices(
    DictLikeMixin[str, ConfigService], RootModel[Dict[str, ConfigService]]
):
    pass


class ConfigNodeRMSpec(BaseModel):
    # our additions
    Role: Literal["rm", "rm-force"]
    # upstream
    model_config = ConfigDict(extra="allow")


class ConfigNodeRemoteDockerConf(BaseModel):
    base_url: Optional[str] = None
    version: Optional[str] = None
    timeout: Optional[str] = None
    tls: Optional[Union[object, bool]] = None
    user_agent: Optional[str] = None
    credstore_env: Optional[Dict[Any, Any]] = None
    use_ssh_client: Optional[bool] = None
    max_pool_size: Optional[int] = None


class ConfigNodeManagerStatus(BaseModel):
    Addr: Optional[str] = None  # listen_addr
    model_config = ConfigDict(extra="allow")


class ConfigNodeSpec(BaseModel):
    Availability: Optional[Literal["active", "pause", "drain"]] = "active"
    Role: Literal["manager", "worker"]
    Labels: Optional[Dict[str, object]] = None
    model_config = ConfigDict(extra="allow")


class ConfigNodeStatus(BaseModel):
    Addr: Optional[str]  # advertise_addr, remote_addrs
    model_config = ConfigDict(extra="allow")


class ConfigNode(BaseModel):
    # my addons
    remote_docker_conf: Optional[ConfigNodeRemoteDockerConf] = None
    # upstream (sorta)
    # https://docs.docker.com/reference/cli/docker/node/demote/
    # https://docs.docker.com/reference/cli/docker/node/promote/
    # https://docs.docker.com/reference/cli/docker/node/update/
    # https://docker-py.readthedocs.io/en/stable/nodes.html
    # https://docker-py.readthedocs.io/en/stable/swarm.html?highlight=join#docker.models.swarm.Swarm.join
    # upstream Swarm.join
    DataPathAddr: Optional[str] = None
    ManagerStatus: Optional[ConfigNodeManagerStatus] = None
    # upstream Node.attrs
    Spec: Union[ConfigNodeSpec, ConfigNodeRMSpec]
    Status: Optional[ConfigNodeStatus] = None
    model_config = ConfigDict(extra="allow")


class ConfigNodes(DictLikeMixin[str, ConfigNode], RootModel[Dict[str, ConfigNode]]):
    pass


class ConfigSwarm(BaseModel):
    # TODO: remove the keys in node init
    # https://docker-py.readthedocs.io/en/stable/swarm.html#docker.models.swarm.Swarm.init
    # Optional("default_addr_pool"): [str],
    # Optional("subnet_size"): int,
    # Optional("data_path_addr"): str,
    # Optional("data_path_port"): int,
    task_history_retention_limit: Optional[int] = None
    snapshot_interval: Optional[int] = None
    keep_old_snapshots: Optional[int] = None
    log_entries_for_slow_followers: Optional[int] = None
    heartbeat_tick: Optional[int] = None
    election_tick: Optional[int] = None
    dispatcher_heartbeat_period: Optional[int] = None
    node_cert_expiry: Optional[int] = None
    # this CA stuff is likely broken. all of the cert
    # Optional("external_ca"): {
    #    "url": str,
    #    "protocol": str,
    #    "options": dict,
    #    Optional("ca_cert"): str,
    # },
    # name: str
    # labels: Optional[Dict[str, object]] = None
    signing_ca_cert: Optional[str] = None
    signing_ca_key: Optional[str] = None
    # Optional("ca_force_rotate"): int,
    # Optional("autolock_managers"): bool,
    # Optional("log_driver"): {"name": str, Optional("options"): dict},


class ConfigPlugin(BaseModel):
    image: str
    settings: dict
    enabled: Optional[bool] = None
    remove: Optional[Union[Literal["force"], bool]] = None


class ConfigPlugins(
    DictLikeMixin[str, ConfigPlugin], RootModel[Dict[str, ConfigPlugin]]
):
    pass


class ConfigJQPool(BaseModel):
    # mine
    plugins: Optional[jqlang_schema] = None
    swarm: Optional[jqlang_schema] = None
    nodes: Optional[jqlang_schema] = None
    # stacks: Optional[jqlang_schema] = None
    # upstream
    volumes: Optional[jqlang_schema] = None
    networks: Optional[jqlang_schema] = None
    services: Optional[jqlang_schema] = None


class ConfigJQPools(
    DictLikeMixin[str, ConfigJQPool], RootModel[Dict[str, ConfigJQPool]]
):
    """jqlang queries on the config file that get appended to each config"""


class ConfigStack(BaseModel):
    # our additions
    #  Use this for making swarms
    jq_pools: ConfigJQPools = ConfigJQPools.model_validate({})
    # overridden
    volumes: ConfigVolumes = ConfigVolumes.model_validate({})
    networks: ConfigNetworks = ConfigNetworks.model_validate({})
    services: ConfigServices = ConfigServices.model_validate({})
    # upstream
    model_config = ConfigDict(extra="allow")


class ConfigStacks(DictLikeMixin[str, ConfigStack], RootModel[Dict[str, ConfigStack]]):
    pass


class Config(BaseModel):
    # our additions
    #  Docker plugin settings
    plugins: Optional[ConfigPlugins] = None
    #  swarm mode settings (based on commands under docker swarm)
    swarm: ConfigSwarm
    #  A docker swarm mode node
    nodes: Optional[ConfigNodes] = None
    #  Corresponds to docker stack ls
    stacks: ConfigStacks = ConfigStacks.model_validate({})
    # overridden
    # upstream


def injest_config(config_file) -> Config:
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
        config = Config.model_validate(parsed_config)
    except ValidationError as e:
        click.echo(f"validation error in config file {config_file.name}\n{e}")
        sys.exit(1)

    return config
