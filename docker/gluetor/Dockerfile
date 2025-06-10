# inspired by docker-tor: https://github.com/leplusorg/docker-tor

FROM alpine:latest

RUN apk update \
 && apk upgrade \
 && apk add tor \
 && apk add bash \
 && apk add curl \
 && apk add python3 \
 && apk add py3-pip \
 && pip3 install requests --break-system-packages \
 && apk add iptables \
 && apk add bind-tools \
 && rm /var/cache/apk/* \
 && chmod 700 /var/lib/tor

VOLUME /resources

EXPOSE 9050

ADD ./torrc /etc/tor/torrc
ADD startscript.sh /startscript.sh
ADD iptables.sh /iptables.sh
ADD https://raw.githubusercontent.com/sbaresearch/scanywhere/main/utils/tor_utils.py .

CMD ["/startscript.sh"]
