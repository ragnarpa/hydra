import hydra.manager as hydra
from hydra.manager.cluster import HydraDockerCluster


def test_hydra_start_cluster(mocker, random_str, random_int):
    with mocker.patch.object(HydraDockerCluster, HydraDockerCluster.start.__name__):
        name = random_str()
        port = random_int()
        proxy_port = random_int()
        stats_port = random_int()

        cluster = hydra.start_cluster(name, port, proxy_port, stats_port)

        cluster.start.assert_called_once()
        assert cluster.name == name
        assert cluster.port == port


def test_hydra_destroy_cluster(mocker, random_str):
    with mocker.patch.object(HydraDockerCluster, HydraDockerCluster.destroy.__name__):
        name = random_str()

        cluster = hydra.destroy_cluster(name)

        cluster.destroy.assert_called_once()
        assert cluster.name == name


def test_hydra_add_node(mocker, random_str):
    with mocker.patch.object(HydraDockerCluster, HydraDockerCluster.add_node.__name__):
        cluster_name = random_str()

        hydra.add_node(cluster_name)

        HydraDockerCluster.add_node.assert_called_once()


def test_hydra_add_service(mocker, random_str, random_int):
    with mocker.patch.object(HydraDockerCluster, HydraDockerCluster.add_service.__name__):
        cluster_name = random_str()
        service_name = random_str()
        image = random_str()
        node_port = random_int()
        service_port = random_int()
        replicas = random_int()

        hydra.add_service(cluster_name, service_name, image, node_port, service_port, replicas)

        HydraDockerCluster.add_service.assert_called_once_with(service_name, image, node_port, service_port, replicas)
