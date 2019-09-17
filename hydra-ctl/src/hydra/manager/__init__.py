from .cluster import HydraCluster
from .cluster import HydraDockerCluster


def start_cluster(name: str, port: int, proxy_port: int, stats_port: int) -> HydraCluster:
    clstr = HydraDockerCluster(name, port, proxy_port, stats_port)
    clstr.start()
    return clstr


def destroy_cluster(name: str) -> HydraCluster:
    clstr = HydraDockerCluster(name)
    clstr.destroy()
    return clstr


def add_node(cluster_name: str) -> dict:
    clstr = HydraDockerCluster(cluster_name)
    return clstr.add_node()


def add_service(cluster_name: str, alias: str, image: str, node_port: int, service_port: int, replicas: int) -> dict:
    clstr = HydraDockerCluster(cluster_name)
    return clstr.add_service(alias, image, node_port, service_port, replicas)
