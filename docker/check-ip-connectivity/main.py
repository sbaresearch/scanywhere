#!/usr/bin/env python3

import os
import time
import socket
import pathlib

import ip_utils

def generate_output_filename(output_dir, ip, country):
    time_str = time.strftime("%Y%m%d-%H%M%S")
    output_str = f"{country}_{ip}_{time_str}.txt"
    output_file = output_dir / output_str
    return output_file

def scan_ip(comments):
    ip, country = ip_utils.get_ip_info(maxwait=60)
    output_file = generate_output_filename(output_dir, ip, country)
    with open(output_file, "w") as out:
        out.write(f"IP is {ip} ({country}) via {comments['VPN_SERVICE_PROVIDER']}\n")

if __name__ == "__main__":
    print("hello")

    input_dir = pathlib.Path("resources")
    output_dir = pathlib.Path("results")

    comments = {
        'VPN_SERVICE_PROVIDER': os.environ.get('VPN_SERVICE_PROVIDER', "undefined"),
        'VPN_TYPE': os.environ.get('VPN_TYPE', "undefined"),
        'GLUETUN_IP': os.environ.get('GLUETUN_IP', "undefined"),
    }

    ip_utils.PREFERED_ADDR = socket.AF_INET
    print("SCAN IPV4 start")
    scan_ip(comments)
    print("SCAN IPV4 finished")

    if not ip_utils.is_ipv6_supported():
        print("IPV6 not supported")
        exit(0)

    ip_utils.PREFERED_ADDR = socket.AF_INET6
    print("SCAN IPV6 start")
    scan_ip(comments)
    print("SCAN IPV6 finished")

    print("bye")
