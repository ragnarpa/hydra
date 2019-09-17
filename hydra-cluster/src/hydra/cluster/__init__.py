import docker
import json
import logging
import random
import redis
import socket
import threading
import typing

from .haproxy import HAProxy


class ClusterError(Exception):
    pass


class NotEnoughNodes(Exception):
    pass


class HydraCluster(object):

    # TODO: Refactor this class into smaller classes like Service, Node, etc

    NODE_DOWN_EVENTS = ['destroy', 'die', 'kill', 'stop']
    NODE_IMAGE = 'docker:dind'

    __lock = threading.Lock()

    def __init__(self):
        self._node = None
        self._network = None
        self._haproxy = None
        self._service_registry = None

        self._docker_client = docker.from_env()

    @property
    def node(self):
        if not self._node:
            self._node = self._docker_client.containers.get(socket.gethostname())
        return self._node

    @property
    def name(self) -> str:
        return self.node.name

    @property
    def network(self):
        if not self._network:
            nw = list(self.node.attrs['NetworkSettings']['Networks'].keys())[0]
            self._network = self._docker_client.networks.get(nw)
        return self._network

    @property
    def nodes(self) -> iter:
        return filter(
            lambda n: n.name.startswith('node-'),
            self._docker_client.containers.list(filters={'network': self.network.name})
        )

    @property
    def node_state(self) -> iter:
        for n in self.nodes:
            yield dict(
                name=n.name,
                ip=n.attrs['NetworkSettings']['Networks'][self.network.name]['IPAddress']
            )

    @property
    def service_registry(self) -> redis.Redis:
        # TODO: Redis should be wrapped behind facade which woulnd't reveal Redis specific interfaces.
        if not self._service_registry:
            self._service_registry = redis.Redis(
                host='redis.{}'.format(self.network.name),
                port=6379
            )
        return self._service_registry

    @property
    def haproxy(self) -> HAProxy:
        if not self._haproxy:
            self._haproxy = HAProxy('haproxy.{}'.format(self.network.name), self._docker_client)
        return self._haproxy

    @property
    def services(self) -> iter:
        return map(json.loads, self.service_registry.mget(self.service_registry.keys()))

    def get_service_config(self, alias) -> dict:
        try:
            return json.loads(self.service_registry.get(alias))
        except:
            return dict(name=alias, nodes=[])

    def get_node_services(self, node_name):
        for service in self.services:
            nodes = service.get('nodes', [])
            if any([True for node in nodes if node['name'] == node_name]):
                yield service

    def unlink_service_from_node(self, alias, node_name):
        srv_cfg = self.get_service_config(alias)
        srv_cfg['nodes'] = [node for node in srv_cfg['nodes'] if node['name'] != node_name]
        # TODO: Redis interfaces leaking in.
        self.service_registry.set(alias, json.dumps(srv_cfg))

    def migrate_services(self, reason, node_name: str):
        logging.info('Starting service relocation from node {}. Reason: {}'.format(node_name, str(reason)))

        for service in self.get_node_services(node_name):
            self.unlink_service_from_node(service['name'], node_name)
            for node in [node for node in service['nodes'] if node['name'] == node_name]:
                logging.info('Trying to redeploy service {} on another node.'.format(service['name']))
                try:
                    self.deploy_service(
                        service['name'],
                        node['service_image'],
                        node['node_port'],
                        node['service_port'],
                        replicas=1
                    )
                    logging.info('Service {!r} deployed on node {!r}.'.format(service['name'], node['name']))
                except Exception as error:
                    logging.error('Could not redeploy service {} on another node.'.format(service['name']))
                    logging.error(error)

    def node_down_monitor(self, node_name: str, handlers: typing.List[typing.Callable], events: typing.List[str]):
        node_events = self._docker_client.events(
            filters={'container': node_name, 'event': events})

        for e in node_events:
            for handler in handlers:
                threading.Thread(target=handler, args=(e, node_name,)).start()
            # Stop reading events for node <node_name> after first down event.
            node_events.close()
            break

        logging.warning('Exiting node down monitor for {}.'.format(threading.current_thread().name))

    def next_node_name(self) -> str:
        i = max([int(n.name.split('.')[0].split('-')[1]) for n in self.nodes] or [0]) + 1
        return 'node-{}.{}'.format(i, self.name)

    def get_free_nodes(self, alias: str) -> iter:
        srv_cfg = self.get_service_config(alias)
        srv_nodes = srv_cfg.get('nodes', [])

        def node_filter(name):
            return lambda item: item['name'] == name

        for n in self.nodes:
            # nodeN -> node-N ...
            k = n.name.split('.')[0].replace('-', '')
            free_on_proxy = next(self.haproxy.get_free_node(alias, k), None) is not None
            free_on_cluster = srv_cfg is None or next(filter(node_filter(n.name), srv_nodes), None) is None

            if free_on_proxy and free_on_cluster:
                yield n

    def create_node(self):
        with HydraCluster.__lock:
            name = self.next_node_name()
            node = self._docker_client.containers.run(
                HydraCluster.NODE_IMAGE,
                name=name,
                hostname=name,
                privileged=True,
                network=self.network.name,
                tty=True,
                stdin_open=True,
                detach=True,
                remove=True
            )

            # Start node down monitor ...
            threading.Thread(
                target=self.node_down_monitor,
                args=(node.name, [self.migrate_services], HydraCluster.NODE_DOWN_EVENTS,),
                name=node.name
            ).start()

            return node

    def deploy_service(self, alias: str, image: str, node_port: int, service_port: int, replicas: int = 1) -> dict:
        logging.info('Deploying %s replicas of service %r with image %r.', replicas, alias, image)

        if alias and not alias.isalnum():
            msg = 'Alias has to be alphanumeric.'
            logging.error(msg)
            raise ValueError(msg)
        if not image:
            msg = 'Image name needed.'
            logging.error(msg)
            raise ValueError(msg)
        if not node_port or not service_port:
            msg = 'Node port or service port missing.'
            logging.error(msg)
            raise ValueError(msg)

        with HydraCluster.__lock:
            nodes_ = list(self.get_free_nodes(alias))
            node_count = len(nodes_)

            logging.info('Count of free nodes is {}'.format(node_count))

            if replicas > node_count:
                raise NotEnoughNodes('Available nodes is {}.'.format(node_count))

            # Spread strategy is just to shuffle nodes :)
            random.shuffle(nodes_)

            srv_cfg = self.get_service_config(alias)

            def deploy():
                node = nodes_.pop()
                service_node_name = '{}.{}'.format(alias, node.name)

                cmd = [
                    'docker', 'run',
                    '-tid', '--rm',
                    '-p', '{}:{}'.format(node_port, service_port),
                    '--name', service_node_name,
                    image
                ]

                # Start service on given node.
                exit_code, output = node.exec_run(cmd)
                if exit_code > 0:
                    raise ClusterError(output)

                logging.info('Service {!r} started on {}:{}.'.format(alias, node.name, node_port))

                # TODO: If service hasn't been yet configured on HAProxy then do it dynamically.
                self.haproxy.register_service(alias, node.name, node_port)

                srv_node_info = dict(
                    name=node.name,
                    service_image=image,
                    node_port=node_port,
                    service_port=service_port
                )

                srv_cfg['nodes'].append(srv_node_info)

            threads = [threading.Thread(target=deploy) for _ in range(0, replicas)]
            [t.start() for t in threads]
            [t.join() for t in threads]

            srv_cfg['endpoints'] = [self.haproxy.url + '/' + alias]

            # TODO: Redis interface is leaking in.
            self.service_registry.set(alias, json.dumps(srv_cfg))

            return srv_cfg
