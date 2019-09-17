import logging

from flask import Flask, request, jsonify, url_for
from . import HydraCluster, NotEnoughNodes

FLASK_DEBUG = True
API_PORT = 8080

logging.basicConfig(filename='hydra-cluster.log', level=logging.DEBUG)

api = Flask(__name__)
cluster = HydraCluster()


@api.route('/node', methods=['POST'])
def node():
    # TODO check if we have enough nodes on HAProxy
    node_ = cluster.create_node()
    d = dict(
        name=node_.name,
        image=node_.attrs['Config']['Image'],
        state=node_.attrs['State']
    )
    return jsonify(d)


@api.route('/state', methods=['GET'])
def state():
    d = {
        'name': cluster.name,
        'nodes': list(cluster.node_state),
        'api': {
            'node': url_for(node.__name__, _external=True),
            'state': url_for(state.__name__, _external=True),
            'service': url_for(service.__name__, _external=True)
        },
        'services': list(cluster.services)
    }

    # TODO: Show also HAProxy state

    return jsonify(d)


@api.route('/service', methods=['POST'])
def service():
    content = request.get_json()

    service_alias = content.get('alias')
    service_image = content.get('image')
    node_port = content.get('node_port')
    service_port = content.get('service_port')
    replicas = content.get('replicas', 1)

    try:
        service_state = cluster.deploy_service(
            service_alias, service_image, node_port, service_port, replicas)
        logging.info('Service %r deployed.', service_alias)
        return jsonify(service_state)
    except (ValueError, NotEnoughNodes) as error:
        return jsonify(dict(error=str(error))), 400


def main():
    api.run(host='0.0.0.0', port=API_PORT, debug=FLASK_DEBUG)
