#!/usr/bin/env python3

import uuid
import time
import requests
import docker
import pathlib
import logging
import random
import json
import argparse
import socket
from contextlib import closing
from utils.ec2_manager import EC2Manager
from utils.hideme import get_hideme_servers
from utils.ip_utils import get_ip_info

PATH_CREDENTIALS = "credentials.json"

GLUETUN_API_PORT = None #8000

def get_config(key, config_path=PATH_CREDENTIALS):
    with open(config_path, "r") as jsonfile:
        json_dict = json.load(jsonfile)
        value = json_dict.get(key)
        if not value:
            logging.error(f"error reading config {key}")
        return value

ENVIRONMENT_BASE = {
    "OPENVPN_IPV6": "on",
    "UPDATER_PERIOD": "24h",
    "DOT": "off"
}

# nordvpn: max 6 devices
ENVIRONMENT_NORD_OPENVPN = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "nordvpn",
    "VPN_TYPE": "openvpn",
    "OPENVPN_USER": get_config("NORD_OPENVPN_USER"),
    "OPENVPN_PASSWORD": get_config("NORD_OPENVPN_PASSWORD")
}
ENVIRONMENT_NORD_WIREGUARD = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "nordvpn",
    "VPN_TYPE": "wireguard",
    "WIREGUARD_PRIVATE_KEY": get_config("NORD_WIREGUARD_PRIVATE_KEY")
}
ENVIRONMENT_NORDVPN = ENVIRONMENT_NORD_OPENVPN

# mullvad: max 5 devices
ENVIRONMENT_MULLVAD_OPENVPN = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "mullvad",
    "VPN_TYPE": "openvpn",
    "OPENVPN_USER": get_config("MULLVAD_OPENVPN_USER"),
    "OPENVPN_CIPHERS": "AES-256-GCM"
}
ENVIRONMENT_MULLVAD_WIREGUARD = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "mullvad",
    "VPN_TYPE": "wireguard",
    "WIREGUARD_PRIVATE_KEY": get_config("MULLVAD_WIREGUARD_PRIVATE_KEY"),
    "WIREGUARD_ADDRESSES": get_config("MULLVAD_WIREGUARD_ADDRESSES")
}
ENVIRONMENT_MULLVAD = ENVIRONMENT_MULLVAD_OPENVPN

# surfshark: unlimited devices
ENVIRONMENT_SURFSHARK_OPENVPN = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "surfshark",
    "VPN_TYPE": "openvpn",
    "OPENVPN_USER": get_config("SURFSHARK_OPENVPN_USER"),
    "OPENVPN_PASSWORD": get_config("SURFSHARK_OPENVPN_PASSWORD")
}
ENVIRONMENT_SURFSHARK_WIREGUARD = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "surfshark",
    "VPN_TYPE": "wireguard",
    "WIREGUARD_PRIVATE_KEY": get_config("SURFSHARK_WIREGUARD_PRIVATE_KEY"),
    "WIREGUARD_ADDRESSES": get_config("SURFSHARK_WIREGUARD_ADDRESSES")
}
ENVIRONMENT_SURFSHARK = ENVIRONMENT_SURFSHARK_OPENVPN

# proton: max 10 devices
ENVIRONMENT_PROTONVPN_OPENVPN = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "protonvpn",
    "VPN_TYPE": "openvpn",
    "OPENVPN_USER": get_config("PROTON_OPENVPN_USER"),
    "OPENVPN_PASSWORD": get_config("PROTON_OPENVPN_PASSWORD")
}
# note: proton supports wg, but every server uses its own keypair and peer addr --> we just use openvpn to get unified access to all servers

# private internet access: unlimited
ENVIRONMENT_PIA_OPENVPN = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "private internet access",
    "VPN_TYPE": "openvpn",
    "OPENVPN_USER": get_config("PIA_OPENVPN_USER"),
    "OPENVPN_PASSWORD": get_config("PIA_OPENVPN_PASSWORD")
}

# hidemyass - max 5 devices
ENVIRONMENT_HIDEMYASS_OPENVPN = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "hidemyass",
    "VPN_TYPE": "openvpn",
    "OPENVPN_USER": get_config("HMA_OPENVPN_USER"),
    "OPENVPN_PASSWORD": get_config("HMA_OPENVPN_PASSWORD")
}

# cyberghost - max 7 devices
ENVIRONMENT_CYBERGHOST_OPENVPN = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER" : "cyberghost",
    "VPN_TYPE" : "openvpn",
    "OPENVPN_USER" : get_config("CYBERGHOST_OPENVPN_USER"),
    "OPENVPN_PASSWORD" : get_config("CYBERGHOST_OPENVPN_PASSWORD"),
    "OPENVPN_KEY" : get_config("CYBERGHOST_OPENVPN_KEY"),
    "OPENVPN_CERT" : get_config("CYBERGHOST_OPENVPN_CERT")
}

# ivpn - max 7 devices
ENVIRONMENT_IVPN_OPENVPN = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "ivpn",
    "VPN_TYPE": "openvpn",
    "OPENVPN_USER": get_config("IVPN_OPENVPN_USER"),
    "OPENVPN_PASSWORD": "ivpn"
}
ENVIRONMENT_IVPN_WG = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "ivpn",
    "VPN_TYPE": "wireguard",
    "WIREGUARD_PRIVATE_KEY": get_config("IVPN_WIREGUARD_PRIVATE_KEY"),
    "WIREGUARD_ADDRESSES": get_config("IVPN_WIREGUARD_ADDRESSES")
}

# hideme - max 10 devices?
ENVIRONMENT_HIDEME_OPENVPN = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "hideme",
    "VPN_TYPE": "openvpn",
    "VPN_ENDPOINT_IP": None,
    #"VPN_ENDPOINT_PORT": 3000,
    "OPENVPN_USER": get_config("HIDEME_OPENVPN_USER"),
    "OPENVPN_PASSWORD": get_config("HIDEME_OPENVPN_PASSWORD"),
    "OPENVPN_CERT": "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",
    "OPENVPN_CIPHERS": "aes-256-cbc",
    "OPENVPN_AUTH": "sha256",
}

# ec2
ENVIRONMENT_BASE_EC2 = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "ec2", # ec2
    "VPN_TYPE": "wireguard"
}

ENVIRONMENT_BASE_WARP = ENVIRONMENT_BASE | {
    "VPN_SERVICE_PROVIDER": "custom",
    "VPN_TYPE": "wireguard",
    "WIREGUARD_PUBLIC_KEY": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
    "WIREGUARD_PRIVATE_KEY": "oP5ispUIZ+MWHM0DpbH67ULWYj8S06OJzcIbp3S4sEE=",
    "WIREGUARD_ADDRESSES": "172.16.0.2/32,2606:4700:110:8d9a:1c15:9ec7:ae5f:bb96/128",
    "VPN_ENDPOINT_IP":"162.159.192.1",
    "VPN_ENDPOINT_PORT":"2408"
}

HIDEME_TEMPLATE = """
client
dev tun
proto udp
remote VPN_ENDPOINT_IP 3000
cipher AES-256-CBC
auth SHA256
resolv-retry infinite
nobind
persist-key
persist-tun
mute-replay-warnings
verb 3
auth-user-pass
reneg-sec 900
remote-cert-tls server
verify-x509-name "*.hide.me" name
tls-version-min 1.2

<ca>
-----BEGIN CERTIFICATE-----
MIIKJDCCBgygAwIBAgIQVc9ekKx5ZIkHcGchmaaVEzANBgkqhkiG9w0BAQ0FADCB
kTELMAkGA1UEBhMCTVkxHDAaBgNVBAgME1dpbGF5YWggUGVyc2VrdXR1YW4xDzAN
BgNVBAcMBkxhYnVhbjEZMBcGA1UECgwQZVZlbnR1cmUgTGltaXRlZDEeMBwGA1UE
CwwVQ2VydGlmaWNhdGUgQXV0aG9yaXR5MRgwFgYDVQQDDA9IaWRlLk1lIFJvb3Qg
Q0EwHhcNMTYwMTE3MjExMDI0WhcNNDYwMTA5MjExMDI0WjCBkTELMAkGA1UEBhMC
TVkxHDAaBgNVBAgME1dpbGF5YWggUGVyc2VrdXR1YW4xDzANBgNVBAcMBkxhYnVh
bjEZMBcGA1UECgwQZVZlbnR1cmUgTGltaXRlZDEeMBwGA1UECwwVQ2VydGlmaWNh
dGUgQXV0aG9yaXR5MRgwFgYDVQQDDA9IaWRlLk1lIFJvb3QgQ0EwggQiMA0GCSqG
SIb3DQEBAQUAA4IEDwAwggQKAoIEAQDX8zVTP6FQ4gJ+4e06bxvxifNHK8ht0RZn
zCNrrwkekpB4ojXDghNfS38oK80RfygC8LXN7SnLv+0xw5dRZ3QVIZJnd/DtX2EF
ZVxMyccJkLj8IEZv4Yx7zPnKI9EcQwo64O7npz28JZAGwexmK1W7ohm9VaAAtUPY
6Ej7k/wsJi2d5BeHzYRrfJX3nEft8hbotwsFLPsngDciS3yE2B5zH/PJOZ5uzr/5
djAbeFktfHR6ywbxE2CYjz2pVUfqvzjzwNj5BJPp3K5iTL/oL1xrAkQ5xSPtHbP0
ZCMmR//PC73cqkI6bAw8YAjvq0CG7wSC3rCfzgz3RGGPHMVUmB+GGu1KZoGisexm
9Y3ovmgubM+eE23aMBObf6tcRp1hSv7+EenlqAbyqQ5JqltWgsjEcV6THRKFmlSS
CP84kZK+nLnoto6MEG8sK9d02+iYWPQbVQ9X7O6pMHgVj7vnOLuW6i+hKT/pcsnU
8yhu2495Q07NDAAeX12dMbHhfLAs+DMtxjkj9SxejCS3Gi/XxON0E1NVVNEcl4yu
TODIJVfh/+uDdUn6v8tP7XmIFlKlfyQzfxND/VlRAep1Tt4i04KAhW0SG5/qaXoP
YROoP7eA0igKI5PxGbUZw/ym0i+1iXHR5XqfavZRM6gpOlDH2D9Mo64JfJTWT8J0
AQ9apVXQZlC9raY5fulvX3TqZ5NDbm4z/hOawDFOmWWjOe2guTj+aMyDS13mpppz
JF5h9JPlvvyb1Z0cjWv5zkW00pcO5qrk2l0kbL4kSoYia+URdpi/pbF30W27JwhQ
oQqjdEcvr7qSYNkpnGSO57qZKS0Rjsnbgk2c8X1gHWqhECCoExBxT55bSKBPvrAw
1jxdct9ZTROcU0Cz39jYT9stYEaozXhzHJmMZReunh1G2sWDqYQST33ljIcqtsDI
DYu6KZorc3jioTHWnd8d/iCwz+vQcnNlyBIqqB9L0i07iQcTUGJ6lcm144JkfTEP
2xY2mFuu14KXq9tI90PzxtodBhu7DodBTtARtwRwJ7O5goME8T29UTDQbjIvZegf
eK3pzlPxdv7X+6jVl4a7Mx8S4FNAnwPa2Dz/y2uEOozRzMSmpjZb7qiVXipoe7aK
QB4oc2kK2oEfWfnF/HcFf3QZSe2fCQKp3DOGk6n9fpPFbR7PFu1Ng16HpoA6l+F3
Pamo4O6v0AxvDavj804dfyykN66Er3bfFVJu3wF/s7lrqjSQa+uGiIQ+TYehCBJY
jzQsFtuKU3/GE4L8xlfgnSUASWkmOVEDwgPon9DUbcLR2fIM9O45Xkhmbq/2YPVw
BlNCu3ScU3Y6lJ3QRNanOrfMIg1l3DZ/jeZmMDlINJvA7arx4XD5AgMBAAGjdjB0
MA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgGGMB0GA1UdDgQWBBTqzyLU
H5gO8ud/EfET7E92x/rJuTAfBgNVHSMEGDAWgBTqzyLUH5gO8ud/EfET7E92x/rJ
uTARBglghkgBhvhCAQEEBAMCAAcwDQYJKoZIhvcNAQENBQADggQBAEs7gwuhUOxo
rVCWcG0lKLWbgj0w/KqTwgAwyIN8Muth3SLF750iQ+U6AWDKY2sBRibYRmM5UUgq
CVL2XShwN7SkuAnkitYU7NDEFr/gQsoEObMo1s7cNtelVcOTKYBqvIHsSw9SX7mr
EoDVWCOW5Gx8/z6luexo6P5iSVvr4xbechQ6SKxpFIrhnE5k+MRDfvRLUyCbCQMg
0zIteC1kVL6Lrfx/JiDjMpDz7zPUFh/gXuqA3FAFN/oaQkhpHroiwgMi6X1qFB7m
/y1Qctb7Tw+h8SfzapRBq1EOxqZ86bGjI35MRxbEgP9SD7fRpo86jpejKS2JXnsf
q1agSSw90H95nzX4ck6DGtKGNiDeNcDrsj98vCImsvO0X6T2eX/sx2ZRANEHcmHt
J+tcdLo+UqoCUkdvCxxnNMYgnlhGhXbfzxeKsgQz5zQDg2XA2uZCNtgg6lQLgvmM
xD+wPVY+ewGnJuz9reSxR9SyMxmpkAA7zqxpdG8HKRKupFxpnoyt17PAilsawMD/
vtCTw1CNbo56oA635MZiNzb/5GO8vp0VDsS5nErL/DP/MEHmt/qZqLCoiStjTE1j
QQsggyl/EH8NbIYQDAQweUMSmvdVBa1qwXSnbSd9xX3AE7RE34gZ1abS1zhXjTkY
C16mj3nkCzCbax3eC5BKctxd4GB7JcpctAzvhWAfKAHAFsc8DLAUM+/S1+UWwOP1
Lq5Z/+ZdXBiMiXbzyyAPILOp89hoF1c4BTmAmpFNCPQTa/kwC4pdSJCXRljfpMBE
pkaKNteAJQZkWC2ACi2tuD6z34uS/yputnLMahyJvTiVa35NvG7yVc/h3/GDanHK
f9h2CSlKc6FrtJNtysXWaVioATSjHLe0AXFLMuFBwlhyivrJaHjVneUOiG2EERVv
TsaQT04Kqschl9tiqvlsXSrqKi2dLvDWEkG3F+nmNCUE4E6VrHCTk3X9Gs/d2AbP
MfcxPbrIt1TLRN+OFG2ivpJtWyHROqWXQG85GVwpplaa4sg80OrX9bu4MYlg5MFk
4RHBAPLe5eJ8YobwPOAD4vnl2yqpgxbEBAiPlX/mXsfbBYLXHsDS/EMPecJ3aqZ3
Wv7y9IeWz9x6h4/AGM2pSbL+FHy4i55o4486CTKuB/6PEnlLAiVfPDkhDpJo0/ta
n+p25b79tbI2iIoa4VqhkFAXpCdujNc/j7f+5wT+PsandEi3vckAvvZjhmTdreev
+nB/J2uzyFLr+6MUrYkPlOEUOnNImqDeXE/ocPFsTHiigV1I+1CUUgLr2MGuFTFm
ZpQyQ6V9oqNU6av+hsD11GYpV8wi4QqWjeBOQayXJ7vcwqE3igyoBI2vMrpwfLlJ
K127pRfgZn0=
-----END CERTIFICATE-----
</ca>

<tls-crypt>
-----BEGIN OpenVPN Static key V1-----
8d25d82e75abbcdd73fb17b2ba5d1af2
2d0e026ac8608ec8e51ecb0b3b1b5dba
8ac1f6e556e4b4e3545e979dd26e2d9d
5bc28c1d75b4e37531aabf5da3cba671
1f8998eb66aa290daab6122bdfcb1aa3
b9b428e722ea6e7edd9b878a5161c555
14e6233d18b5cc34e859ecb5852b34ed
6e539d64676edf9ad79470795ae73184
05d93554de1063aec1df6420709c2dcc
79511fa9c5e82de09d560f7d92001ea2
75e4b3e9b6ce19687968b4813d6a9d61
a48311658de88d651edb4eab447d73f6
b209d144a3343a2c992b09c7501cad77
cdf5c6b3be5f9919854bb10182c86794
9df929173b8e98aeea9ffe277eddd7f7
936232e1e44c9feb7a3a2753ed05c90b
-----END OpenVPN Static key V1-----
</tls-crypt>
"""

started_containers = list()

def find_free_port(host="127.0.0.1"):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((host, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def get_gluetun_ip_info(url="http://localhost:8000/v1/publicip/ip", sleeptime=2, ip_field="public_ip", country_field="country", maxwait=60*10):
    return get_ip_info(url, sleeptime, ip_field, country_field, maxwait)

def build_container(client, tag):
    logging.info(f"build {tag} container...")
    client.images.build(path = f"docker/{tag}/", tag=tag)
 

def run_gluetun(client, environment, api_port=8000, network="", image="qmcgaw/gluetun:latest"):
    cur_dir = pathlib.Path(".")
    container = client.containers.run(
        image = image,
        network = network,
        cap_add = ["NET_ADMIN"],
        devices = ["/dev/net/tun:/dev/net/tun"],
        volumes = [f"{cur_dir.absolute()}/docker/gluetun:/gluetun",
                   f"{cur_dir.absolute()}/docker/gluetun/post-rules.txt:/iptables/post-rules.txt"],
        ports = {f"{api_port}/tcp": ('127.0.0.1', api_port)}, #if not network else {},
        sysctls = {"net.ipv6.conf.all.disable_ipv6": "0"}, #if network != "host" else {},
        environment = environment | {"HTTP_CONTROL_SERVER_ADDRESS" : f":{api_port}"},
        detach = True,
        remove = True
    )
    started_containers.append(container.name)
    return container.name

def run_gluetun_extended(client, environment, container_list, network="", image="qmcgaw/gluetun:latest"):
    api_port = GLUETUN_API_PORT or find_free_port()
    logging.info(f"start gluetun (api port {api_port})")
    gluetun_name = run_gluetun(client, environment, api_port, network, image)
    time.sleep(5)
    assert is_container_running(client, gluetun_name)
    ip, country = get_gluetun_ip_info(f"http://localhost:{api_port}/v1/publicip/ip")
    environment['GLUETUN_IP'] = ip
    logging.info(f"gluetun[{gluetun_name}] connected with {country} ({ip})")
    return gluetun_name

def warponize_container(client, gluetun_name, network=""):
    logging.info(f"warporize gluetun container [{gluetun_name}]")
    container = client.containers.get(gluetun_name)
    container.exec_run("/gluetun/wgcf register --accept-tos --config /tmp/wgcf-account.toml")
    container.exec_run("/gluetun/wgcf generate --profile /tmp/wgcf-account.toml --config /tmp/wgcf-account.toml")
    config = container.exec_run("cat /tmp/wgcf-account.toml").output
    #logging.info(f"got config...{config}")
    params = dict()
    for line in config.decode().splitlines():
        if "=" in line:
            key, value = [x.strip() for x in line.split("=", 1)]
            if key in params:
                params[key] = f"{params[key]},{value}"
            else:
                params[key] = value
                
    gateway_ip = container.attrs.get("NetworkSettings", {}).get("IPAddress") or container.attrs.get("NetworkSettings", {}).get("Networks", {}).get(network).get("IPAddress")
    environment = ENVIRONMENT_BASE | {
        "VPN_SERVICE_PROVIDER": "custom",
        "VPN_TYPE": "wireguard",
        "WIREGUARD_PUBLIC_KEY": params["PublicKey"],
        "WIREGUARD_PRIVATE_KEY": params["PrivateKey"],
        "WIREGUARD_ADDRESSES": params["Address"],
        "VPN_ENDPOINT_IP":"162.159.192.1", #cloudflare ip
        "VPN_ENDPOINT_PORT":"2408",
        "WIREGUARD_MTU": params["MTU"],
        "WARP_GATEWAY_IP":gateway_ip
    }
    #logging.info(f"run warporizer...{environment}")
    #network = f"container:{gluetun_name}"#
    gluetun_name = run_gluetun_extended(client, environment, network, image="gluetun-warp")
    return gluetun_name, environment['GLUETUN_IP']

def run_image(client, gluetun_name, environment, image_tag, remove = False):
    cur_dir = pathlib.Path(".")
    container = client.containers.run(
        image = f"{image_tag}:latest",
        network = f"container:{gluetun_name}",
        volumes = [f"{cur_dir.absolute()}/docker/{image_tag}/resources:/{image_tag}/resources:ro",
                   f"{cur_dir.absolute()}/docker/{image_tag}/results:/{image_tag}/results"],
        sysctls = {
            "net.ipv6.conf.all.disable_ipv6": "0"
        },
        environment = environment | {
            "PYTHONUNBUFFERED": "1"
        },
        detach = True,
        remove = remove
    )
    started_containers.append(container.name)
    return container.name

def get_container_status(client, container_name):
    try:
        container = client.containers.get(container_name)
        return container.status
    except:
        return None

def is_container_running(client, container_name):
    return get_container_status(client, container_name) in ['created', "running", "restarting"]

def stop_container(container_name):
    try:
        container = client.containers.get(container_name)
        container.stop()
    except:
        pass

def stop_all_started_containers():
    for c in reversed(started_containers):
        stop_container(c)

def prune_docker_images(client, image_label):
    try:
        return client.images.prune(filters={"label": image_label})
    except:
        pass

def start_containers(client, environment, target_image, network="", warp_mode=False):
    # check if image is present:
    try:
        client.images.get(target_image)
    except:
        logging.error(f"unknown image {target_image}")
        exit(-1)

    gluetun_environment = environment.copy()
    if gluetun_environment.get('VPN_SERVICE_PROVIDER') in ['ec2']:
        gluetun_environment['VPN_SERVICE_PROVIDER'] = 'custom'
    elif gluetun_environment.get('VPN_SERVICE_PROVIDER') in ['hideme']:
        gluetun_environment['VPN_SERVICE_PROVIDER'] = 'custom'
    try:
        gluetun_name = run_gluetun_extended(client, gluetun_environment, network)
        if warp_mode:
            gluetun_name, warp_ip = warponize_container(client, gluetun_name, network)
            gluetun_environment['GLUETUN_IP'] = warp_ip
            gluetun_environment['VPN_SERVICE_PROVIDER'] = "warp"
            gluetun_environment['VPN_TYPE'] = "wireguard"
        
        measurement_name = run_image(client, gluetun_name, gluetun_environment, target_image)
        logging.info(f"measurement launched: image[{target_image}] within container[{measurement_name}]")
        while(is_container_running(client, measurement_name)):
            time.sleep(1)
        logging.info(f"measurement finished: image[{target_image}] within container[{measurement_name}]")
    except TimeoutError:
        logging.error("gluetun did not get an ip address..")
        pass
    except AssertionError:
        logging.error("gluetun was not properly started...?")
        pass
    except:
        logging.error("unknown error occured...")
        #import traceback
        #print(traceback.format_exc())
        pass
    stop_all_started_containers()

def read_gluetun_servers(json_path="docker/gluetun/servers.json"):
  parsed = None
  while True:
    try:
        with open(json_path) as file:
            content = file.read()
            parsed = json.loads(content)
            if parsed:
                return parsed
            else:
                logging.error("no content read from servers.json")
    except:
        logging.error("exception parsing gluetun servers.json")
        time.sleep(5)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s'
    )
    vpn_services = {
        'nord_open' : ENVIRONMENT_NORD_OPENVPN,
        'nord_wg' : ENVIRONMENT_NORD_WIREGUARD,
        'mullvad_open' : ENVIRONMENT_MULLVAD_OPENVPN,
        'mullvad_wg' : ENVIRONMENT_MULLVAD_WIREGUARD,
        'surfshark_open' : ENVIRONMENT_SURFSHARK_OPENVPN,
        'surfshark_wg' : ENVIRONMENT_SURFSHARK_WIREGUARD,
        'proton_open' : ENVIRONMENT_PROTONVPN_OPENVPN,
        'pia_open' : ENVIRONMENT_PIA_OPENVPN,
        'hma_open' : ENVIRONMENT_HIDEMYASS_OPENVPN,
        'cyberghost_open' : ENVIRONMENT_CYBERGHOST_OPENVPN,
        'ivpn_open' : ENVIRONMENT_IVPN_OPENVPN,
        'ivpn_wg' : ENVIRONMENT_IVPN_WG,
        'hideme_open': ENVIRONMENT_HIDEME_OPENVPN,
        'ec2' : ENVIRONMENT_BASE_EC2,
        'surfshark_open_india' : ENVIRONMENT_SURFSHARK_OPENVPN | {"SERVER_COUNTRIES" : "India"},
        'proton_open_india' : ENVIRONMENT_PROTONVPN_OPENVPN | {"SERVER_COUNTRIES" : "India"},
        'hma_missing' : ENVIRONMENT_HIDEMYASS_OPENVPN | {"SERVER_COUNTRIES" : "Russia, Belarus, Faroe Islands, Antiguaand Barbuda, Bermuda, Dominican Republic, Jordan, Kuwait, Oman, Maldives, Sudan, Tanzania, Namibia"},
        'surfshark_germany' : ENVIRONMENT_SURFSHARK_OPENVPN | {"SERVER_COUNTRIES" : "Germany"},
        'warp_wg': ENVIRONMENT_BASE_WARP
    }

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--target_image', default='vowifi-geoblocking-scan-epdgs')
    parser.add_argument('--vpn_service',
                        choices=vpn_services.keys(),
                        required=True)
    parser.add_argument('--server_selection', choices=['random', 'normalized'], default='normalized')
    parser.add_argument('--prune_containers', action='store_true')
    parser.add_argument('--warp_mode', action='store_true')
    args = parser.parse_args() #, warpmode=False

    client = docker.from_env()
    
    if args.prune_containers:
        prune_docker_images(client, args.target_image)

    # build local image
    build_container(client, args.target_image)
    
    network=""
    if args.warp_mode:
        # build_warp_container
        build_container(client, "gluetun-warp")
        network = client.networks.create(f"{uuid.uuid4()}").name
    
    while(True):
        tmp_path = None

        environment = vpn_services[args.vpn_service].copy()
        if args.vpn_service == 'ec2':
            ec2_manager = EC2Manager()
            client_config_dict = ec2_manager.start_instance_wg()
            environment |= client_config_dict
        elif args.vpn_service == 'hideme_open':
            host_list = get_hideme_servers()
            target_host = random.choice([h[0] for h in host_list.values()])
            logging.info(f"resolve {target_host}")
            target_ip = socket.gethostbyname(target_host)
            environment['VPN_ENDPOINT_IP'] = target_ip
            logging.info(f"pin host to {environment['VPN_ENDPOINT_IP']}")
            tmp_filename = f"{uuid.uuid4()}.conf"
            tmp_path = pathlib.Path(".") / "docker" / "gluetun" / tmp_filename
            file_content = HIDEME_TEMPLATE.replace('VPN_ENDPOINT_IP', target_ip)
            with open(tmp_path, "w") as file:
                file.write(file_content)
            environment["OPENVPN_CUSTOM_CONFIG"] = f"/gluetun/{tmp_filename}"
        elif environment["VPN_SERVICE_PROVIDER"] == 'custom':
            pass
        elif 'SERVER_COUNTRIES' in environment:
            environment['SERVER_COUNTRIES'] = random.choice(environment['SERVER_COUNTRIES'].split(",")).strip()
            logging.info(f"pin country to {environment['SERVER_COUNTRIES']}")
        elif 'SERVER_REGIONS' in environment:
            environment['SERVER_REGIONS'] = random.choice(environment['SERVER_REGIONS'].split(",")).strip()
            logging.info(f"pin region to {environment['SERVER_REGIONS']}")
        elif args.server_selection == 'normalized':
            gluetun_servers = read_gluetun_servers()
            service = environment['VPN_SERVICE_PROVIDER']
            available_countries = list(dict.fromkeys([d.get('country') for d in gluetun_servers[service]['servers']]))
            available_regions = list(dict.fromkeys([d.get('region') for d in gluetun_servers[service]['servers']]))
            if any(available_countries):
                environment |= {'SERVER_COUNTRIES' : random.choice(available_countries)}
                logging.info(f"pin country to {environment['SERVER_COUNTRIES']}")
            elif any(available_regions):
                environment |= {'SERVER_REGIONS' : random.choice(available_regions)}
                logging.info(f"pin region to {environment['SERVER_REGIONS']}")

        start_containers(client, environment, args.target_image, network, args.warp_mode)

        if tmp_path:
            tmp_path.unlink()