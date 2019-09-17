import argparse
import json
import sys

import hydra.manager as hydra


def hydra_error(func):
    def wrapped(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as error:
            print(error, file=sys.stderr)
    return wrapped


@hydra_error
def start_cluster(args):
    hydra.start_cluster(args.name, args.port, args.proxy_port, args.stats_port)


@hydra_error
def destroy_cluster(args):
    hydra.destroy_cluster(args.name)


@hydra_error
def add_node(args):
    node = hydra.add_node(args.cluster)
    print(json.dumps(node, indent=2))


@hydra_error
def add_service(args):
    srv = hydra.add_service(
        args.cluster, args.alias, args.image,
        args.node_port, args.service_port, args.replicas)

    print(json.dumps(srv, indent=2))


def main():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()

    # cluster
    parser_cluster = subparsers.add_parser('cluster')
    subparsers_cluster = parser_cluster.add_subparsers()

    # cluster start
    parser_start_cluster = subparsers_cluster.add_parser('start')
    parser_start_cluster.add_argument('name')
    parser_start_cluster.add_argument('--port', required=True, dest='port', type=int)
    parser_start_cluster.add_argument('--proxy-port', dest='proxy_port', type=int, default=8888)
    parser_start_cluster.add_argument('--stats-port', dest='stats_port', type=int, default=9999)
    parser_start_cluster.set_defaults(func=start_cluster)

    # cluster destroy
    parser_destroy_cluster = subparsers_cluster.add_parser('destroy')
    parser_destroy_cluster.add_argument('name')
    parser_destroy_cluster.set_defaults(func=destroy_cluster)

    # node
    parser_node = subparsers.add_parser('node')
    subparsers_node = parser_node.add_subparsers()

    # node add
    parser_add_node = subparsers_node.add_parser('add')
    parser_add_node.add_argument('--cluster', required=True)
    parser_add_node.set_defaults(func=add_node)

    # service
    parser_service = subparsers.add_parser('service')
    subparsers_service = parser_service.add_subparsers()

    # service add
    parser_add_service = subparsers_service.add_parser('add')
    parser_add_service.add_argument('alias')
    parser_add_service.add_argument('--image', required=True)
    parser_add_service.add_argument('--cluster', required=True)
    parser_add_service.add_argument('--node-port', required=True, dest='node_port', type=int)
    parser_add_service.add_argument('--service-port', required=True, dest='service_port', type=int)
    parser_add_service.add_argument('--replicas', default=1, type=int)
    parser_add_service.set_defaults(func=add_service)

    args = parser.parse_args()
    args.func(args)
