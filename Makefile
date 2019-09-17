hydra-docker-haproxy-image:
	$(MAKE) -C haproxy all

hydra-docker-base-image:
	docker build -t hydra-base --build-arg DOCKER_GROUP_ID=$(shell getent group docker | cut -d: -f3) .

hydra-docker-cluster-image: hydra-docker-base-image
	$(MAKE) -C hydra-cluster hydra-docker-cluster-image

.PHONY: hydra-ctl
hydra-ctl:
	$(MAKE) -C hydra-ctl install

create-test-cluster:
	hydra-ctl cluster start test --port 4000
	sleep 1 && hydra-ctl node add --cluster test
	sleep 1 && hydra-ctl node add --cluster test
	sleep 1 && hydra-ctl node add --cluster test
	sleep 1 && hydra-ctl node add --cluster test
	sleep 1 && hydra-ctl node add --cluster test

hydra-ctl-test:
	$(MAKE) -C hydra-ctl test

hydra-cluster-test:
	$(MAKE) -C hydra-cluster test

test: hydra-ctl-test hydra-cluster-test

pull-images:
	docker pull docker
	docker pull haproxy
	docker pull redis

destroy-test-cluster:
	hydra-ctl cluster destroy test

clean:
	$(MAKE) -C hydra-ctl clean
	$(MAKE) -C hydra-cluster clean

clean-images:
	docker container prune -f
	docker image ls --format "{{.Repository}}:{{.Tag}}" | xargs docker image rm -f

all: pull-images hydra-docker-haproxy-image hydra-docker-cluster-image hydra-ctl

