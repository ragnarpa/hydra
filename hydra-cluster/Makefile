sdist:
	python3 setup.py sdist

hydra-docker-cluster-image: sdist
	docker build -t hydra-cluster --build-arg DOCKER_GROUP_ID=$(shell getent group docker | cut -d: -f3) .

test:
	python3 setup.py test

clean:
	find $(shell pwd) -name "__pycache__" -type d | xargs rm -fr
	rm -fr dist src/hydra_cluster.egg-info
