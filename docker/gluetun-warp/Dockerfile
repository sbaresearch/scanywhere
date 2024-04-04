FROM qmcgaw/gluetun:latest

COPY rewrite_gateway.sh /

RUN set -ex;\
    chmod a+x /rewrite_gateway.sh

ENTRYPOINT [ "sh", "/rewrite_gateway.sh" ]