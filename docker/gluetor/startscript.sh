#!/bin/sh

# docker-tor

# sometimes inheriting nameserver settings from host did not work properly
# just use google dns for downloading tor relay data
echo "nameserver 8.8.8.8" > /etc/resolv.conf

# pinning exit relay node to target country that is provided via env
./tor_utils.py --write_torrc --exit_country $ExitCountry

# block icmp/udp traffic and forward everything else over tor
./iptables.sh

# make sure no dns traffic is routed via other dns servers
echo "nameserver 127.0.0.1" > /etc/resolv.conf

# start tor
su - tor -s /bin/sh -c "/usr/bin/tor -f /etc/tor/torrc"