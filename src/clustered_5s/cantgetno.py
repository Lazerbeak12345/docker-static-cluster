def satisfy_apps(config):
    raise NotImplementedError(satisfy_apps)


def satisfy_nodes(config) -> tuple[object, object]:
    raise NotImplementedError(satisfy_nodes)


def satisfy_resource_pools(config):
    raise NotImplementedError(satisfy_resource_pools)


def satisfy_config(config):
    config, nodes = satisfy_nodes(config)
    config = satisfy_apps(config)
    config = satisfy_resource_pools(config)
    return config, nodes
