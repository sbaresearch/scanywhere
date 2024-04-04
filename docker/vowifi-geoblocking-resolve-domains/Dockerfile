#FROM alpine
#FROM debian
FROM mvance/unbound


WORKDIR /vowifi-geoblocking-resolve-domains/

# make unbound recursive
# COPY resources/unbound.conf /opt/unbound/etc/unbound/unbound.conf

# debian
RUN apt-get update && apt-get install -y git build-essential dnsutils net-tools python3 python3-pip \
   && git clone --depth=1 https://github.com/blechschmidt/massdns.git \
   && cd massdns \
   && make

COPY requirements.txt .

RUN set -ex;\
    pip install -r requirements.txt --break-system-packages

COPY resolve_domains.py .

RUN set -ex;\
    chmod a+x resolve_domains.py

COPY entrypoint.sh .
RUN set -ex;\
    chmod a+x entrypoint.sh

#CMD ["unbound"]

#ENTRYPOINT ["./vowifi-geoblocking-resolve-domains/resolve_domains.py"]
#ENTRYPOINT ["/bin/sh"]
ENTRYPOINT ["/vowifi-geoblocking-resolve-domains/entrypoint.sh"]