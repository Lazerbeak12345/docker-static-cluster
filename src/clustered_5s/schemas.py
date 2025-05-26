from schema import Schema, Optional, Or

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
            # upstream (sorta)
            # https://docs.docker.com/reference/cli/docker/swarm/join/#options
            # TODO: Optional("availability"): Or(
            # TODO: Schema("active"), Schema("pause"), Schema("drain")
            # TODO: ),
            # TODO: Optional("advertise-addr"): str,
            # TODO: Optional("listen-addr"): str,
            # TODO: Optional("data-path-addr"): str,
            # TODO: Optional("data-path-port"): str,
            # "id": str,
            # "hostname": str,
            # "role": Or(Schema("manager"), Schema("worker")),
            ## ip address?
            ## Optional("advertise-addr"): str,
            ## ip address?
            ## Optional("data-path-addr"): str,
            # "platform": {
            #    # TODO: other osese
            #    # "os": Or(Schema("windows")),
            #    "os": str,
            #    # "arch": Or(Schema("x86_64"))
            #    "arch": str,
            # },
            # TODO: labels
            # "labels": {str: str},
        }
    ),
    # my additions
    #  special role to remove stuff
    Schema({"id": str, "hostname": str, "role": "force-rm"}),
)

config_nodes_schema = Schema({Optional(str): config_node_schema})

config_swarm_schema = Schema(
    {
        # https://docs.docker.com/reference/cli/docker/swarm/update/#options
        # TODO: Optional("autolock"): bool,
        # TODO: Optional("max-snapshots"): int,
        # TODO: Optional("snapshot-interval"): int,
        # TODO: Optional("task-history-limit"): int,
        # https://docs.docker.com/reference/cli/docker/swarm/ca/
        # TODO: Optional("ca"): {
        # TODO: Optional("cert"): str,
        # TODO: Optional("key"): str,
        # TODO: Optional("cert-expiry"): str,
        # TODO: Optional("external-ca"): [str],
        # TODO: OUR cli may need --rotate
        # TODO: },
        # https://docs.docker.com/reference/cli/docker/swarm/init/
        # TODO: Optional("autolock"): bool,
        # TODO: Optional("default-addr-pool"): [str],
        # TODO: Optional("default-addr-pool-mask-length"): int,
        # TODO: Optional("dispatcher-heartbeat"): int,
        # TODO: --force-new-cluster should be part of OUR cli
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
