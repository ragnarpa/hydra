FROM docker

ARG DOCKER_GROUP_ID

RUN apk update && apk add python3 shadow
RUN groupmod -g 3000 ping && find / -group 999 -exec chgrp -h ping {} \;
RUN addgroup -g $DOCKER_GROUP_ID docker && adduser -DH -G docker hydra
