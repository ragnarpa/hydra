import docker
import docker.errors
import json
import requests

CONTENT_TYPE_APPLICATION_JSON = {'Content-Type': 'application/json'}


class ClusterError(Exception):
    pass


class HydraCluster(object):

    def __init__(self, name: str, port: int = None):
        self.name = name
        self._port = port
        self.destroyed = False

    @property
    def port(self):
        return self._port

    def start(self):
        raise NotImplementedError()

    def add_node(self):
        raise NotImplementedError()

    def add_service(self, alias: str, name: str, node_port: int, service_port: int, replicas: int = 1):
        raise NotImplementedError()

    def destroy(self):
        raise NotImplementedError()


class HydraDockerCluster(HydraCluster):

    def __init__(self, name: str, port: int = None, proxy_port: int = 8888, stats_port: int = 9999):
        super().__init__(name, port)

        self._docker_client = docker.from_env()

        # Cluster network shares the name with cluster.
        self._network = self.name

        self._api_node_name = 'api.{}'.format(self.name)
        self._api_image = 'hydra-cluster'
        self._api_port = 8080

        self._lb_node_name = 'haproxy.{}'.format(self.name)
        self._lb_image = 'hydra-haproxy'
        self._lb_port = proxy_port
        self._lb_haproxy_port = 8888
        self._lb_stats_port = stats_port
        self._lb_haproxy_stats_port = 9999

        self._redis_node_name = 'redis.{}'.format(self.name)
        self._redis_image = 'redis'

    @property
    def api_url(self):
        ip = self.api_server.attrs['NetworkSettings']['Ports']['{}/tcp'.format(self._api_port)][0]['HostIp']
        port = self.api_server.attrs['NetworkSettings']['Ports']['{}/tcp'.format(self._api_port)][0]['HostPort']
        return 'http://{}:{}'.format(ip, port)

    @property
    def members(self):
        return self._docker_client.containers.list(filters={'network': self._network})

    @property
    def api_server(self):
        return self.member(self._api_node_name)

    def member(self, name):
        try:
            return self._docker_client.containers.get(name)
        except docker.errors.NotFound as error:
            raise ClusterError(error)

    def add_node(self) -> dict:
        if self.destroyed:
            raise ClusterError('Cluster is destroyed. Can\'t add node.')

        payload = {}

        r = requests.post(
            self.api_url + '/node',
            headers=CONTENT_TYPE_APPLICATION_JSON,
            data=json.dumps(payload)
        )

        res = json.loads(r.text or '{}')
        res.update(dict(status_code=r.status_code))

        return res

    def add_service(self, alias: str, image: str, node_port: int = 0, service_port: int = 0, replicas: int = 1) -> dict:
        if self.destroyed:
            raise ClusterError('Cluster is destroyed. Can\'t add service.')
        if not self.api_server:
            raise ClusterError('Can\'t connect to API server')
        if node_port <= 0 or service_port <= 0:
            raise ValueError('\'node_port\' and \'service_port\' has to be greater than 0.')
        if replicas <= 0:
            raise ValueError('\'replicas\' has to be greater than 0.')

        payload = {
            'alias': alias,
            'image': image,
            'replicas': replicas,
            'node_port': node_port,
            'service_port': service_port
        }

        r = requests.post(
            self.api_url + '/service',
            headers=CONTENT_TYPE_APPLICATION_JSON,
            data=json.dumps(payload)
        )

        res = json.loads(r.text or '{}')
        res.update(dict(status_code=r.status_code))

        return res

    def destroy(self) -> bool:
        if self.api_server:
            print('Stopping cluster {} ...'.format(self.name))

            networks = self.api_server.attrs['NetworkSettings']['Networks'].keys()

            # Remove all nodes including API node itself.
            for n in self.members:
                print('Stopping node {!r} ...'.format(n.name))
                try:
                    n.stop()
                except Exception as error:
                    print(error)

            # Remove all related networks too.
            for nw in networks:
                print('Removing network {!r} ...'.format(nw))
                try:
                    self._docker_client.networks.get(nw).remove()
                except docker.errors.NotFound:
                    pass

            self.destroyed = True

        return self.destroyed

    def start(self):
        try:
            self._start_network()
            self._start_redis()
            self._start_load_balancer()
            self._start_api_server()
        except Exception as error:
            self.destroy()
            raise ClusterError(error)

    def _start_network(self):
        print('Starting cluster network {!r} ...'.format(self._network))
        self._docker_client.networks.create(self._network)

    def _start_redis(self):
        print('Starting redis ...')
        self._docker_client.containers.run(
            self._redis_image,
            name=self._redis_node_name,
            network=self._network,
            tty=True,
            stdin_open=True,
            detach=True,
            remove=True,
            hostname=self._redis_node_name
        )

    def _start_api_server(self):
        print('Starting cluster API at http://localhost:{} '.format(self.port))
        self._docker_client.containers.run(
            self._api_image,
            ports={self._api_port: self.port},
            volumes={
                '/var/run/docker.sock': {'bind': '/var/run/docker.sock', 'mode': 'rw'}
            },
            volumes_from=[self._lb_node_name],
            name=self._api_node_name,
            network=self._network,
            tty=True,
            stdin_open=True,
            detach=True,
            remove=True,
            hostname=self._api_node_name
        )

    def _start_load_balancer(self):
        print('Starting cluster load balancer at http://localhost:{}'.format(self._lb_port))
        self._docker_client.containers.run(
            self._lb_image,
            ports={self._lb_haproxy_port: self._lb_port, self._lb_haproxy_stats_port: self._lb_stats_port},
            name=self._lb_node_name,
            network=self._network,
            tty=True,
            stdin_open=True,
            detach=True,
            remove=True,
            hostname=self._lb_node_name
        )
