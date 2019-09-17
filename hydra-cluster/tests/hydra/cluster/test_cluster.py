import docker
import json
import pytest
import redis

import hydra.cluster.haproxy as haproxy
from hydra.cluster import HydraCluster
from tests.conftest import random_str


@pytest.fixture
def nodes(mocker):
    n1 = mocker.MagicMock()
    n1.name = 'node-1.test'
    n1.exec_run = mocker.MagicMock(return_value=(0, random_str(),))

    n2 = mocker.MagicMock()
    n2.name = 'node-2.test'
    n2.exec_run = n1.exec_run

    return [n1, n2]


def test_hydra_cluster(mocker):
    mocker.patch.object(docker, docker.from_env.__name__)
    clstr = HydraCluster()

    assert clstr._node is None
    assert clstr._network is None
    assert clstr._haproxy is None
    assert clstr._service_registry is None
    assert clstr._docker_client is not None


def test_hydra_cluster_node(mocker):
    mocker.patch.object(docker, docker.from_env.__name__)
    clstr = HydraCluster()

    assert clstr._node is None
    assert clstr.node is not None
    assert clstr._node is not None


def test_hydra_cluster_name(mocker):
    mocker.patch.object(docker, docker.from_env.__name__)
    clstr = HydraCluster()

    assert clstr.name is not None


def test_hydra_cluster_network(mocker):
    clstr = sut(mocker, [], [])

    assert clstr._network is None
    assert clstr.network is not None
    assert clstr._network is not None

    clstr._docker_client.networks.get.assert_called_once_with(clstr.network.name)


def test_hydra_cluster_nodes(mocker, nodes):
    clstr = sut(mocker, nodes, [])

    assert len(list(clstr.nodes)) == 2
    clstr._docker_client.containers.list.assert_called_once_with(
        **dict(filters={'network': clstr.name})
    )


def test_hydra_cluster_node_state(mocker, nodes):
    clstr = sut(mocker, nodes, [])

    node_state = list(clstr.node_state)

    assert len(node_state) == 2
    assert node_state[0].get('name') in [n.name for n in nodes]
    assert node_state[0].get('ip') is not None
    assert node_state[1].get('name') in [n.name for n in nodes]
    assert node_state[1].get('ip') is not None
    assert node_state[0].get('name') != node_state[1].get('name')
    assert node_state[0].get('ip') != node_state[1].get('ip')


def test_hydra_cluster_service_registry(mocker):
    mocker.patch.object(redis, redis.Redis.__name__)
    mocker.patch.object(
        HydraCluster,
        HydraCluster.network.fget.__name__,
        new_callable=mocker.PropertyMock
    )

    clstr = HydraCluster()

    assert clstr._service_registry is None
    assert clstr.service_registry is not None
    assert clstr._service_registry is not None


def test_hydra_cluster_haproxy(mocker):
    mocker.patch.object(
        HydraCluster,
        HydraCluster.network.fget.__name__,
        new_callable=mocker.PropertyMock
    )

    clstr = HydraCluster()

    assert clstr._haproxy is None
    assert clstr.haproxy is not None
    assert clstr._haproxy is not None


def test_hydra_cluster_services(mocker):
    service = {random_str(): random_str()}
    mget_ret_val = [json.dumps(service)]
    mocker.patch.object(
        HydraCluster,
        HydraCluster.service_registry.fget.__name__,
        new_callable=mocker.PropertyMock,
        return_value=mocker.MagicMock(
            mget=mocker.MagicMock(return_value=mget_ret_val),
            keys=mocker.MagicMock(return_value=[])
        )
    )

    clstr = HydraCluster()
    services = clstr.services

    assert list(services) == [service]


def test_hydra_cluster_next_node_name(mocker, nodes):
    clstr = sut(mocker, nodes, [])

    assert clstr.next_node_name() == 'node-3.test'


def test_hydra_cluster_get_free_nodes(mocker, nodes):
    haproxy_nodes = [dict(svname='node1')]

    clstr = sut(mocker, nodes, haproxy_nodes)
    nodes = list(clstr.get_free_nodes(random_str()))

    assert len(nodes) == 1
    assert nodes[0].name in [n.name for n in nodes]


def test_hydra_cluster_create_node(mocker, nodes):
    mocker.patch.object(
        HydraCluster,
        HydraCluster.node_down_monitor.__name__
    )

    expected_node_name = 'node-3.test'
    expected_network_name = 'test'

    clstr = sut(mocker, nodes, [])

    node = clstr.create_node()

    clstr._docker_client.containers.run.assert_called_once_with(
        HydraCluster.NODE_IMAGE,
        **dict(
            name=expected_node_name,
            hostname=expected_node_name,
            privileged=True,
            network=expected_network_name,
            tty=True,
            stdin_open=True,
            detach=True,
            remove=True
        )
    )
    clstr.node_down_monitor.assert_called_once_with(
        node.name,
        [clstr.migrate_services],
        HydraCluster.NODE_DOWN_EVENTS
    )


def test_hydra_cluster_deploy_service(mocker, nodes):
    haproxy_nodes = [dict(svname='node1'), dict(svname='node2')]

    clstr = sut(mocker, nodes, haproxy_nodes)

    srv_name = random_str()
    img_name = random_str()
    srv_port = 10000
    node_port = 10001
    srv_cfg = clstr.deploy_service(
        srv_name,
        img_name,
        node_port,
        srv_port
    )

    assert srv_cfg.get('name') == srv_name
    assert srv_cfg.get('endpoints')[0].endswith(srv_name)
    assert len(srv_cfg.get('nodes')) == 1
    assert srv_cfg.get('nodes')[0].get('name') in [n.name for n in nodes]
    assert srv_cfg.get('nodes')[0].get('service_image') == img_name
    assert srv_cfg.get('nodes')[0].get('node_port') == node_port
    assert srv_cfg.get('nodes')[0].get('service_port') == srv_port


def sut(mocker, docker_nodes: list, haproxy_nodes: list, cluster_name: str = 'test') -> HydraCluster:
    # Mock docker
    mock_docker = mocker.MagicMock()
    mock_docker.containers = mocker.MagicMock()
    mock_node = mocker.MagicMock(
        attrs=dict(
            NetworkSettings=dict(
                Networks={
                    cluster_name: dict(IPAddress=random_str())
                }
            )
        )
    )
    mock_node.name = cluster_name
    mock_docker.containers.get = lambda x: mock_node
    mock_docker.containers.list = mocker.MagicMock(return_value=docker_nodes)
    mock_docker.networks = mocker.MagicMock()
    mock_network = mocker.MagicMock()
    mock_network.name = cluster_name
    mock_docker.networks.get = mocker.MagicMock(return_value=mock_network)

    # Mock Redis
    mock_redis = mocker.MagicMock()
    mock_redis.get = mocker.MagicMock(return_value={'name': random_str(), 'nodes': docker_nodes})

    # Mock HAProxy
    mocker.patch.object(
        haproxy.HAProxy,
        haproxy.HAProxy.get_free_nodes.__name__,
        return_value=iter(haproxy_nodes)
    )
    mocker.patch.object(
        haproxy.HAProxy,
        haproxy.HAProxy.url.fget.__name__,
        new_callable=mocker.PropertyMock,
        return_value=random_str()
    )
    mocker.patch.object(
        haproxy.HAProxy,
        haproxy.HAProxy.register_service.__name__
    )

    clstr = HydraCluster()
    clstr._docker_client = mock_docker
    clstr._service_registry = mock_redis
    return clstr