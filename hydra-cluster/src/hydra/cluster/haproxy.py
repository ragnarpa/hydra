import csv
import docker
import io
import logging
import socket

FIELDNAMES = [
    '# pxname', 'svname', 'qcur', 'qmax', 'scur', 'smax', 'slim', 'stot', 'bin', 'bout', 'dreq', 'dresp', 'ereq',
    'econ', 'eresp', 'wretr', 'wredis', 'status', 'weight', 'act', 'bck', 'chkfail', 'chkdown', 'lastchg', 'downtime',
    'qlimit', 'pid', 'iid', 'sid', 'throttle', 'lbtot', 'tracked', 'type', 'rate', 'rate_lim', 'rate_max',
    'check_status', 'check_code', 'check_duration', 'hrsp_1xx', 'hrsp_2xx', 'hrsp_3xx', 'hrsp_4xx', 'hrsp_5xx',
    'hrsp_other', 'hanafail', 'req_rate', 'req_rate_max', 'req_tot', 'cli_abrt', 'srv_abrt', 'comp_in', 'comp_out',
    'comp_byp', 'comp_rsp', 'lastsess', 'last_chk', 'last_agt', 'qtime', 'ctime', 'rtime', 'ttime', 'agent_status',
    'agent_code', 'agent_duration', 'check_desc', 'agent_desc', 'check_rise', 'check_fall', 'check_health',
    'agent_rise', 'agent_fall', 'agent_health', 'addr', 'cookie', 'mode', 'algo', 'conn_rate', 'conn_rate_max',
    'conn_tot', 'intercepted', 'dcon', 'dses', 'wrew', 'connect', 'reuse', 'cache_lookups', 'cache_hits', ''
]

# Needs to be in sync with haproxy/Dockerfile and haproxy/haproxy.cfg.
PORT = 8888
STATS_PORT = 9999


class HAProxy(object):

    def __init__(
            self, host: str, docker_client: docker.DockerClient,
            socket_file: str = '/var/run/haproxy/admin.sock'):
        self._socket_file = socket_file
        self._host = host
        self._docker_client = docker_client

    @property
    def url(self) -> str:
        node_ = self._docker_client.containers.get(self._host)
        ip = node_.attrs['NetworkSettings']['Ports']['{}/tcp'.format(PORT)][0]['HostIp']
        port = node_.attrs['NetworkSettings']['Ports']['{}/tcp'.format(PORT)][0]['HostPort']
        return 'http://{}:{}'.format(ip, port)

    def send(self, cmd) -> str:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(self._socket_file)

        cmd = bytes('{}\n'.format(cmd), 'ascii')

        s.send(cmd)

        data = s.recv(1024)
        res = ''

        while True:
            res += data.decode('ascii')
            data = s.recv(1024)
            if not data:
                break

        s.close()

        return res

    def backend_nodes(self, service_name) -> list:
        cmd = 'show stat'

        def _filter(item):
            return item['svname'].startswith('node') and item['# pxname'] == service_name

        with io.StringIO(self.send(cmd)) as stat:
            reader = csv.DictReader(stat, delimiter=',', fieldnames=FIELDNAMES)
            return list(filter(_filter, reader))

    def get_free_nodes(self, service_name) -> iter:
        return filter(lambda item: item['status'] == 'MAINT', self.backend_nodes(service_name))

    def get_free_node(self, service_name, node_name) -> iter:
        return filter(lambda item: item['svname'] == node_name, self.get_free_nodes(service_name))

    def register_service(self, alias, node_name, service_port):
        node_addr = socket.gethostbyname(node_name)

        # Point respective backend node to point to service endpoint.
        # The name format of backend node in HAProxy is nodeN.
        # The name format of cluster node is node-N.network.
        be_node = node_name.split('.')[0].replace('-', '')
        params = dict(
            alias=alias,
            node=be_node,
            addr=node_addr,
            port=service_port
        )
        set_server_addr = 'set server {alias}/{node} addr {addr} port {port}'.format(**params)
        res = self.send(set_server_addr)
        logging.info(res)

        # Put backend node into rotation.
        set_ready = 'set server {alias}/{node} state ready'.format(**params)
        res = self.send(set_ready)
        logging.info(res)
