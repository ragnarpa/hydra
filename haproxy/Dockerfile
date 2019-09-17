FROM haproxy
ARG DOCKER_GROUP_ID
COPY haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg
RUN  addgroup haproxy \
     && adduser --gecos --disabled-password --disabled-login --no-create-home --ingroup haproxy haproxy \
     && mkdir -p /run/haproxy/ \
     && mkdir -p /var/lib/haproxy/
RUN  addgroup --gid $DOCKER_GROUP_ID docker
VOLUME /var/run/haproxy
EXPOSE 8888 9999