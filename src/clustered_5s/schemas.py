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

config_node_schema = Schema(
    {
        "mode": Or(Schema("manager"), Schema("worker"), Schema("force-rm"))
        # Optional("availability"): "drain"
    }
)

config_nodes_schema = Schema({str: config_node_schema})

config_schema = Schema(
    {
        # our additions
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
