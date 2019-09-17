FROM docker

ARG DOCKER_GROUP_ID

# Set the working directory to /hydra-cluster
WORKDIR /hydra-cluster

# Copy the contents of dist/ the container at /hydra-cluster
ADD haproxy.py dist/ /hydra-cluster/

RUN apk update \
    && apk add shadow \
    && groupmod -g 3000 ping \
    && find / -group 999 -exec chgrp -h ping {} \;
RUN apk update \
    && apk add python3 socat \
    && addgroup -g $DOCKER_GROUP_ID docker \
    && adduser -DH -G docker hydra \
    && pip3 install --trusted-host pypi.python.org hydra-cluster*.tar.gz \
    && chown hydra .

EXPOSE 8080

USER hydra

# Run hydra-cluster when the container launches
CMD ["hydra-cluster"]
