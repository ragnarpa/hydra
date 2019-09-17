import docker
import pytest
import requests
from hydra.manager.cluster import HydraCluster, HydraDockerCluster, ClusterError


def test_hydra_cluster_without_port(random_str):
    name = random_str()

    clstr = HydraCluster(name)

    assert clstr.name == name
    assert not clstr.destroyed
    assert not clstr.port


def test_hydra_cluster_with_port(random_str, random_int):
    name = random_str()
    port = random_int()

    clstr = HydraCluster(name, port)

    assert clstr.name == name
    assert clstr.port == port
    assert not clstr.destroyed


def test_hydra_docker_cluster(mocker, random_str):
    mocker.patch.object(docker, docker.from_env.__name__)
    name = random_str()

    clstr = HydraDockerCluster(name)

    docker.from_env.assert_called_once()
    assert clstr.name == name
    assert not clstr.destroyed
    assert not clstr.port
    assert clstr._lb_port == 8888
    assert clstr._lb_stats_port == 9999
    assert clstr._network == name
    assert clstr._api_node_name == 'api.{}'.format(name)
    assert clstr._api_image == 'hydra-cluster'
    assert clstr._api_port == 8080
    assert clstr._lb_node_name == 'haproxy.{}'.format(name)
    assert clstr._lb_image == 'hydra-haproxy'
    assert clstr._redis_node_name == 'redis.{}'.format(name)
    assert clstr._redis_image == 'redis'


def test_hydra_docker_cluster_api_url(mocker, random_str, random_int):
    host_ip = random_str()
    host_port = random_int()
    attrs = {
        'NetworkSettings': {
            'Ports': {
                '8080/tcp': [{'HostIp': host_ip, 'HostPort': host_port}]
            }
        }
    }
    mocker.patch.object(docker, docker.from_env.__name__)
    mocker.patch.object(
        HydraDockerCluster, HydraDockerCluster.api_server.fget.__name__,
        new_callable=mocker.PropertyMock, return_value=mocker.MagicMock(attrs=attrs))

    clstr = HydraDockerCluster('test')

    assert clstr.api_url == 'http://{}:{}'.format(host_ip, host_port)


def test_hydra_docker_cluster_members(mocker, random_str):
    name = random_str()
    containers = [name]
    mocker.patch.object(
        docker, docker.from_env.__name__,
        return_value=mocker.MagicMock(containers=mocker.MagicMock(
            list=lambda *args, **kwargs: {'containers': containers, 'kwargs': kwargs}))
    )

    clstr = HydraDockerCluster(name)

    res = clstr.members
    assert res['containers'] == containers
    assert res['kwargs']['filters']['network'] == name


def test_hydra_docker_cluster_api_server(mocker, random_str):
    ret_val = random_str()
    mocker.patch.object(docker, docker.from_env.__name__)
    mocker.patch.object(HydraDockerCluster, HydraDockerCluster.member.__name__, return_value=ret_val)

    clstr = HydraDockerCluster(random_str())

    assert clstr.api_server == ret_val
    clstr.member.assert_called_once_with(clstr._api_node_name)


def test_hydra_docker_cluster_add_node(mocker, random_str):
    mocker.patch.object(docker, docker.from_env.__name__)
    mocker.patch.object(
        requests, requests.post.__name__,
        return_value=mocker.MagicMock(text='{}', status_code=200)
    )

    clstr = HydraDockerCluster(random_str())

    assert clstr.add_node() == dict(status_code=200)


def test_hydra_docker_cluster_add_service_cluster_destroyed(mocker, random_str):
    mocker.patch.object(docker, docker.from_env.__name__)

    clstr = HydraDockerCluster(random_str())

    clstr.destroyed = True

    with pytest.raises(ClusterError):
        clstr.add_service(random_str(), random_str())


def test_hydra_docker_cluster_add_service_not_api_server(mocker, random_str):
    mocker.patch.object(docker, docker.from_env.__name__)
    mocker.patch.object(
        HydraDockerCluster, HydraDockerCluster.api_server.fget.__name__,
        new_callable=mocker.PropertyMock(return_value=None))

    clstr = HydraDockerCluster(random_str())

    with pytest.raises(ClusterError):
        clstr.add_service(random_str(), random_str())


def test_hydra_docker_cluster_add_service_node_port_elt_0(mocker, random_str):
    mocker.patch.object(docker, docker.from_env.__name__)

    clstr = HydraDockerCluster(random_str())

    with pytest.raises(ValueError):
        clstr.add_service(random_str(), random_str(), node_port=0)

    with pytest.raises(ValueError):
        clstr.add_service(random_str(), random_str(), node_port=-1)


def test_hydra_docker_cluster_add_service_service_port_elt_0(mocker, random_str):
    mocker.patch.object(docker, docker.from_env.__name__)

    clstr = HydraDockerCluster(random_str())

    with pytest.raises(ValueError):
        clstr.add_service(random_str(), random_str(), service_port=0)

    with pytest.raises(ValueError):
        clstr.add_service(random_str(), random_str(), service_port=-1)


def test_hydra_docker_cluster_add_service_replicast_elt_0(mocker, random_str):
    mocker.patch.object(docker, docker.from_env.__name__)

    clstr = HydraDockerCluster(random_str())

    with pytest.raises(ValueError):
        clstr.add_service(random_str(), random_str(), replicas=0)

    with pytest.raises(ValueError):
        clstr.add_service(random_str(), random_str(), replicas=-1)


def test_hydra_docker_cluster_add_service(mocker, random_str, random_int):
    mocker.patch.object(docker, docker.from_env.__name__)
    mocker.patch.object(
        requests, requests.post.__name__,
        return_value=mocker.MagicMock(text='{}', status_code=200))

    clstr = HydraDockerCluster(random_str())

    assert clstr.add_service(
        random_str(), random_str(), node_port=random_int(), service_port=random_int()) == dict(status_code=200)


def test_hydra_docker_cluster_destroy(mocker, random_str):
    attrs = {
        'NetworkSettings': {
            'Networks': {
                random_str(): random_str(),
                random_str(): random_str()
            }
        }
    }
    mocker.patch.object(docker, docker.from_env.__name__)
    mocker.patch.object(
        HydraDockerCluster, HydraDockerCluster.api_server.fget.__name__,
        new_callable=mocker.PropertyMock, return_value=mocker.MagicMock(attrs=attrs))
    mocker.patch.object(
        HydraDockerCluster, HydraDockerCluster.members.fget.__name__,
        new_callable=mocker.PropertyMock(return_value=[mocker.MagicMock()]))

    clstr = HydraDockerCluster(random_str())

    assert clstr.destroy()


def test_hydra_docker_cluster_start(mocker, random_str):
    mocker.patch.object(HydraDockerCluster, HydraDockerCluster._start_network.__name__)
    mocker.patch.object(HydraDockerCluster, HydraDockerCluster._start_redis.__name__)
    mocker.patch.object(HydraDockerCluster, HydraDockerCluster._start_api_server.__name__)
    mocker.patch.object(HydraDockerCluster, HydraDockerCluster._start_load_balancer.__name__)

    clstr = HydraDockerCluster(random_str())

    clstr.start()

    clstr._start_network.assert_called_once()
    clstr._start_redis.assert_called_once()
    clstr._start_api_server.assert_called_once()
    clstr._start_load_balancer.assert_called_once()


def test_hydra_docker_cluster_start_fail_raises(mocker, random_str):
    mocker.patch.object(HydraDockerCluster, HydraDockerCluster._start_network.__name__, side_effect=Exception('Network exists!'))
    mocker.patch.object(HydraDockerCluster, HydraDockerCluster._start_redis.__name__)
    mocker.patch.object(HydraDockerCluster, HydraDockerCluster._start_api_server.__name__)
    mocker.patch.object(HydraDockerCluster, HydraDockerCluster._start_load_balancer.__name__)
    mocker.patch.object(HydraDockerCluster, HydraDockerCluster.destroy.__name__)

    clstr = HydraDockerCluster(random_str())

    with pytest.raises(ClusterError):
        clstr.start()

    clstr.destroy.assert_called_once()