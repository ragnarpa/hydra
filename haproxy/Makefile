all:
	docker build -t hydra-haproxy --build-arg DOCKER_GROUP_ID=$(shell getent group docker | cut -d: -f3) .
