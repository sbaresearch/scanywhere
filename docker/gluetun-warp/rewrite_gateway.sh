#!/bin/sh

# rewrite gateway
route del default
route add default gw ${WARP_GATEWAY_IP} eth0
echo "successfully set gateway to ${WARP_GATEWAY_IP}"

#actual entrypoint
/gluetun-entrypoint