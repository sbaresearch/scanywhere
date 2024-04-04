#!/usr/bin/env python3

import boto3
import time
import logging
from urllib.parse import urlparse

import json
import socket
from contextlib import closing

import os
import random

#wg
from base64 import urlsafe_b64encode
import codecs
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

PATH_CREDENTIALS = "credentials.json"
URL_DEADMAN_SWITCH_SHELLSCRIPT = "https://raw.githubusercontent.com/sbaresearch/scanywhere/utils/deadman_switch.sh"
URL_DEADMAN_SWITCH_SERVICE = "https://raw.githubusercontent.com/sbaresearch/scanywhere/utils/deadman_switch.service"


VPC_NAME="VPC-EPHEMERAL-WG"
SECURITY_GROUP_NAME="SG-EPHEMERAL-WG"
SUBNET_NAME="SUBNET-EPHEMERAL-WG"
PORT_WG=51820


def is_port_open(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(10)
        if sock.connect_ex((host, port)) == 0:
            #print("port open")
            return True
        else:
            #print("port closed")
            return False


class EC2Manager():
    SCRIPT_HEADER = '''#!/bin/bash
    yum -y install socat;
    '''

    def __init__(self, id=None, key=None): #region='eu-central-1'):
        # read public key
        with open('ssh_key.pub', 'r') as f:
            PUBKEY = f.read()
        if not PUBKEY:
            PUBKEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDDDRfcyC7mH3FMZ5IgdoMFI5g4aOl5rroAs0e+jJMYl2i+mtSpaZ7wkjo7uDgDARKdyDGshqq+yhUdZuzp/MX8av5XW4bZr8EKOULqMNo5jw2tSwtnMU0NNiCsPw8hT6ynnBJqJ9+9bfZuWK65h3oG9XonR+Bqh4hRVSls3jPk+/YUNicN98o02cMzerlfyGgssWvsG3wdk/gTWingzZTOciIHaG7bGq0Gz1Hh+LrSFbF2f4Z3zIg4D3C+8zpkAYjTbTI/L3KNB4vYJhgEEyTWb5lVZp34/G8+Z5Sn/HBkgd6JA0HkaivZKlelqQa6P5vkGvMi8LLi+tWzg+gwHK01 mahatma@XPS-15-9570"

        all_regions = boto3.session.Session().get_available_regions('ec2')
        region = random.choice(all_regions)
        key = os.environ.get('EC2_ID')
        if key is None:
            with open(PATH_CREDENTIALS, "r") as jsonfile:
                #os.environ.get('EC2_ID') # does not work because env is isolated in namespace; maybe fix it by linking env file to ns?
                json_dict = json.load(jsonfile)
                id = json_dict.get('EC2_ID')  
                key = json_dict.get('EC2_KEY')
        self.ec2r = boto3.resource(
            'ec2',
            aws_access_key_id=id,
            aws_secret_access_key=key,
            region_name=region
        )
        self.ec2c = boto3.client(
            'ec2',
            aws_access_key_id=id,
            aws_secret_access_key=key,
            region_name=region
        )
        self.instance = None

    def get_all_instance_types(self):
        # https://stackoverflow.com/questions/33120348/boto3-aws-api-listing-available-instance-types
        '''Yield all available EC2 instance types in region <region_name>'''
        describe_args = {}
        while True:
            describe_result = self.ec2c.describe_instance_types(**describe_args)
            yield from [i for i in describe_result['InstanceTypes']]
            if 'NextToken' not in describe_result:
                break
            describe_args['NextToken'] = describe_result['NextToken']

    def get_apropriate_instance_types(self, name_filter=["nano", "micro"], architecture_filter=["x86_64"]):
        instance_types = sorted(self.get_all_instance_types(), key=lambda d: d.get('MemoryInfo',dict()).get('SizeInMiB'))
        #instance_types = list(self.get_all_instance_types())
        if name_filter:
            instance_types = [i for i in instance_types if any(t in i.get('InstanceType') for t in name_filter)]
        if architecture_filter:
            instance_types = [i for i in instance_types if any(t in i.get('ProcessorInfo', dict()).get('SupportedArchitectures') for t in architecture_filter)]
        return instance_types

    def prepare_security_group(self):
        # check if resources are already created in this region
        vpcs = self.ec2r.vpcs.filter(Filters=[{"Name": "tag:Name", "Values": [VPC_NAME]}])
        vpc = next((x for x in vpcs), None)
        if vpc:
            sgs = vpc.security_groups.filter(Filters=[{"Name": "tag:Name", "Values": [SECURITY_GROUP_NAME]}])
            sg = next((x for x in sgs), None)

            subnets = vpc.subnets.filter(Filters=[{"Name": "tag:Name", "Values": [SUBNET_NAME]}])
            subnet = next((x for x in subnets), None)
            if sg and subnet:
                return sg.group_id, subnet.id
            
        # no resources found --> create apropriate ones
        # https://biancatamayo.me/blog/creating-a-vpc-using-boto3-with-ipv6/
        vpc = self.ec2r.create_vpc(CidrBlock='10.0.0.0/16', AmazonProvidedIpv6CidrBlock=True) #,  TagSpecifications=[{'Tags':[{'Key': 'Name', 'Value': VPC_NAME}]}])
        vpc.create_tags(Tags=[{"Key": "Name", "Value": VPC_NAME}])
        ipv6_subnet_cidr = vpc.ipv6_cidr_block_association_set[0]['Ipv6CidrBlock']
        ipv6_subnet_cidr = ipv6_subnet_cidr[:-2] + '64'
        subnet = vpc.create_subnet(CidrBlock='10.0.0.0/24', Ipv6CidrBlock=ipv6_subnet_cidr) #, MapPublicIpOnLaunch=True, AssignIpv6AddressOnCreation=True)
        subnet.create_tags(Tags=[{"Key": "Name", "Value": SUBNET_NAME}])
        subnet.meta.client.modify_subnet_attribute(SubnetId=subnet.id, MapPublicIpOnLaunch={"Value": True})
        subnet.meta.client.modify_subnet_attribute(SubnetId=subnet.id, AssignIpv6AddressOnCreation={"Value": True})
        internet_gateway = self.ec2r.create_internet_gateway()
        internet_gateway.attach_to_vpc(VpcId=vpc.vpc_id)
        #route_table = vpc.create_route_table()
        route_table = next(iter(vpc.route_tables.all()))
        route_ig_ipv4 = route_table.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=internet_gateway.internet_gateway_id)
        route_ig_ipv6 = route_table.create_route(DestinationIpv6CidrBlock='::/0', GatewayId=internet_gateway.internet_gateway_id)
        route_table.associate_with_subnet(SubnetId=subnet.id)
        
        # creating a new security group not neccessary since vpc will automatically create a default group
        # sg = vpc.create_security_group(GroupName=SECURITY_GROUP_NAME, Description='EC2 Security Group')
        sg = next(iter(vpc.security_groups.all()))
        ip_ranges = [{  
            'CidrIp': '0.0.0.0/0'
        }]
        ip_v6_ranges = [{  
            'CidrIpv6': '::/0'
        }]
        permissions = [{  
            'IpProtocol': 'UDP',
            'FromPort': PORT_WG,
            'ToPort': PORT_WG,
            'IpRanges': ip_ranges,
            'Ipv6Ranges': ip_v6_ranges
        },
        {  
            'IpProtocol': 'TCP',
            'FromPort': 22,
            'ToPort': 22,
            'IpRanges': ip_ranges,
            'Ipv6Ranges': ip_v6_ranges
        },
        ]
        sg.authorize_ingress(IpPermissions=permissions)    
        sg.create_tags(Tags=[{"Key": "Name", "Value": SECURITY_GROUP_NAME}])
        return sg.group_id, subnet.id
    
    def get_image_id(self, image_name):
        images = self.ec2r.images.filter(Filters=[{"Name": "name", "Values": ['debian-11-amd64-20230515-1381']}])
        image = next((x for x in images), None)
        return image.id
    
    def start_instance_startup_script(self, startup_script):
        security_group_id, subnet_id = self.prepare_security_group()
        instance_type = self.get_apropriate_instance_types()[0].get('InstanceType')
        image_id = self.get_image_id('debian-11-amd64-20230515-1381')
        instance = self.ec2r.create_instances(
            ImageId=image_id, #'ami-0b0c5a84b89c4bf99', #'ami-07151644aeb34558a',
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            SecurityGroupIds=[security_group_id],
            SubnetId=subnet_id,
            UserData=startup_script,
            InstanceInitiatedShutdownBehavior='terminate'
            #KeyName='aws_xps'
        )
        self.instance = instance[0]
        logger.info(f"wait until instance {self.instance.id} is up and running")
        self.instance.wait_until_running()
        self.instance.reload() #refresh info, to get public ip addr
        logger.info(f"instance running, ip addresses are {*self.get_ip(),}")

    def start_instance_port_forward(self, port_forwards):
        startup_script = EC2Manager.SCRIPT_HEADER
        for p in port_forwards:
            startup_script += EC2Manager.get_portforward_command(p.get('src_port'), p.get('target_host'), p.get('target_port'))
        self.start_instance_startup_script(startup_script)

    def start_instance_wg(self):
        server_config_file, client_config_dict = EC2Manager.wg_genconfig()
        startup_script = EC2Manager.get_wg_setup_command(server_config_file)
        self.start_instance_startup_script(startup_script)
        client_config_dict['VPN_ENDPOINT_IP'] = self.get_ip()[0]
        return client_config_dict

    def wait_for_portforward(self, port):
        ip = self.get_ip()[0]
        while(not is_port_open(ip, port)):
            time.sleep(1)
            
    def start_instance_forward(self, target_host, ports=[80, 443]):
        port_forwards = []
        for p in ports:
            port_forwards.append( {'src_port': p, 'target_host':target_host})
        self.start_instance_port_forward(port_forwards)
        self.wait_for_portforward(ports[0])

    def start_instance_forward_web(self, url):
        domain = urlparse(url).hostname #netloc
        self.start_instance_forward(domain, [80,443])
         
    def start_instance_forward_dns(self, dns_server):
        self.start_instance_forward(dns_server, [53])

    def stop_instance(self):
        logger.info("stopping ec2 instance")
        self.instance.terminate()
        self.instance.wait_until_terminated()

    def get_ip(self):
        if self.instance:
            return list(filter(lambda v: v is not None, [self.instance.public_ip_address, self.instance.ipv6_address]))
        return None

    @staticmethod
    def get_portforward_command(src_port, target_host, target_port = None):
        if not target_port:
            target_port = src_port
        script_portforward = f'''
        sysctl -w net.ipv6.bindv6only=1;
        socat tcp4-listen:{src_port},reuseaddr,fork tcp4-connect:{target_host}:{target_port} &
        socat udp4-listen:{src_port},reuseaddr,fork udp4:{target_host}:{target_port} &
        socat tcp6-listen:{src_port},reuseaddr,fork tcp6-connect:{target_host}:{target_port} &
        socat udp6-listen:{src_port},reuseaddr,fork udp6:{target_host}:{target_port} &
        '''
        return script_portforward
    
    @staticmethod
    def wg_genkey():
        # generate private key
        private_key = X25519PrivateKey.generate()
        pubkey = private_key.public_key().public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        
        public_key_encoded = codecs.encode(pubkey, 'base64').decode('utf8').strip()
        private_key_encoded = codecs.encode(private_key.private_bytes(encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw, encryption_algorithm=serialization.NoEncryption()), 'base64').decode('utf8').strip()

        return private_key_encoded, public_key_encoded

    @staticmethod
    def wg_genconfig(network_v4="172.19.12.", network_v6="fd86:ea04:1115::"):
        server_priv, server_pub = EC2Manager.wg_genkey()
        client_priv, client_pub = EC2Manager.wg_genkey()

        server_private_ip_v4 = f"{network_v4}1/24"
        client_private_ip_v4 = f"{network_v4}2/32"
        
        server_private_ip_v6 = f"{network_v6}1/64"
        client_private_ip_v6 = f"{network_v6}2/128"

        server_config_file = f'''[Interface]
        Address = {server_private_ip_v4},{server_private_ip_v6}
        PrivateKey = {server_priv}
        ListenPort = {PORT_WG}
        PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o $(ip route list | grep default | awk '{{print $5}}') -j MASQUERADE; ip6tables -A FORWARD -i %i -j ACCEPT; ip6tables -t nat -A POSTROUTING -o $(ip route list | grep default | awk '{{print $5}}') -j MASQUERADE
        PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o $(ip route list | grep default | awk '{{print $5}}') -j MASQUERADE; ip6tables -D FORWARD -i %i -j ACCEPT; ip6tables -t nat -D POSTROUTING -o $(ip route list | grep default | awk '{{print $5}}') -j MASQUERADE

        [Peer]
        PublicKey = {client_pub}
        AllowedIPs = {client_private_ip_v4},{client_private_ip_v6}

        '''
        client_config_dict = {
            'VPN_ENDPOINT_IP': None,
            'VPN_ENDPOINT_PORT': PORT_WG,
            'WIREGUARD_PUBLIC_KEY': server_pub,
            'WIREGUARD_PRIVATE_KEY': client_priv,
            'WIREGUARD_ADDRESSES': f"{client_private_ip_v4},{client_private_ip_v6}"
        }
        return server_config_file, client_config_dict
    
    @staticmethod
    def get_wg_setup_command(server_config_file):
        script_setup = f'''#!/bin/bash

        # add pubkey for troubleshooting via ssh
        mkdir -p /home/admin/.ssh/
        printf "{EC2Manager.PUBKEY}\n" | tee -a /home/admin/.ssh/authorized_keys

        # install wiregguard
        apt update
        apt install -y wireguard curl

        # enable forwarding
        sysctl -w net.ipv4.ip_forward=1
        sysctl -w net.ipv6.conf.all.forwarding=1
        sysctl -w net.ipv6.conf.$(ip route list | grep default | awk '{{print $5}}').accept_ra=2

        # setup wireguard config
        mkdir -p /etc/wireguard/
        printf "{server_config_file}" | tee /etc/wireguard/wg0.conf
        wg-quick up wg0

        curl {URL_DEADMAN_SWITCH_SHELLSCRIPT} > /usr/bin/deadman_switch.sh
        sed -i -e 's/\r$//' /usr/bin/deadman_switch.sh
        chmod +x /usr/bin/deadman_switch.sh

        curl {URL_DEADMAN_SWITCH_SERVICE} > /lib/systemd/system/deadman_switch.service
        systemctl daemon-reload
        systemctl enable deadman_switch.service
        systemctl start deadman_switch.service
        '''
        return script_setup



if __name__ == '__main__':
    manager = EC2Manager()
    #instance.start_instance_startup_script("")
    manager.start_instance_wg()