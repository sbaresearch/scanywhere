#!/usr/bin/env python3
import os
import time
import requests
import subprocess
from pathlib import Path

MASSDNS_BIN = Path("/vowifi-geoblocking-resolve-domains/massdns/bin/massdns")
AUTH_SCRIPT = Path("/vowifi-geoblocking-resolve-domains/massdns/scripts/auth-addrs.sh")
HOSTLIST_FILE = Path("/vowifi-geoblocking-resolve-domains/resources/hosts.txt")
UNBOUND_FILE = Path("/vowifi-geoblocking-resolve-domains/resources/local_unbound.txt")
OUTPUT_DIR = Path("/vowifi-geoblocking-resolve-domains/results/")
TMP_DIR = Path("/tmp/massdns")

def get_ip_info(url="https://wtfismyip.com/json", sleeptime=2, ip_field="YourFuckingIPAddress", country_field="YourFuckingCountryCode", maxwait=60*10):
    time_start = time.time()
    response = None
    while not response:
        try:
            #print(f"requsting {url} ...")
            r = requests.get(url, timeout=30)
            #print(r.text)
            response = r.json()
            ip = response[ip_field]
            country = response[country_field]
            return ip, country
        except:
            response = None
            if time.time() - time_start > maxwait:
                raise TimeoutError()
            time.sleep(sleeptime)

def get_authoritative_nameservers(domain, path="auth_dns.txt"):
    file_ = open(path, "w")
    subprocess.run([AUTH_SCRIPT, domain], stdout=file_)
    return path

def run_massdns(file_host_list, file_dns_list, output_file, query_type="A"):
    with open(output_file.with_suffix(".log"), "w") as file_:
        result = subprocess.run([MASSDNS_BIN, '-s', '100', '-r', file_dns_list.absolute(), '-t', query_type, '-o', 'S', '-w', output_file.absolute(), file_host_list.absolute()], stdout=file_, stderr=file_)
        print(result)

def grep_cname_results(results_file, cname_tmp):
    #with open(cname_tmp, "w") as file_:
        #result = subprocess.run(["grep", "CNAME", results_file, "|", "awk", "'{print $3}'"], stdout=file_, stderr=file_)
        #result = subprocess.run(["grep", "CNAME", results_file], capture_output=True)
        #print(result)
        #if not result.returncode:
        #    result = subprocess.run(["awk", "'{print $3}'"], input=result.stdout, stdout=file_, stderr=file_)
        #    return cname_tmp
    rc = os.system(f"grep CNAME {str(results_file.absolute())}" + " | awk '{print $3}' > " + str(cname_tmp.absolute()))
    if os.stat(cname_tmp).st_size > 0:
        return cname_tmp
        
def append_file(input_file, output_file):
    with open(input_file, "r") as input:
        with open(output_file, "a+") as output:
            output.write(input.read())

def extract_ips(input_file, output_file, query_type):
    os.system(f"grep ' {query_type} ' {str(input_file.absolute())}" + " | awk '{print $3}' | sort | uniq -u > " + str(output_file.absolute()))


if __name__ == "__main__":
    ip, country = get_ip_info("https://wtfismyip.com/json", maxwait=60)
    time_str = time.strftime("%Y%m%d-%H%M%S") + f"_{country}_{ip}"
    OUTPUT_DIR = OUTPUT_DIR / time_str
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    #auth_dns_file = get_authoritative_nameservers("3gppnetwork.org", OUTPUT_DIR / "auth_dns.txt")

    for query_type in ["A", "AAAA"]:
        with open(OUTPUT_DIR / "vpn_config.txt", "w") as output:
            output.write("\n".join([
                os.environ.get('VPN_SERVICE_PROVIDER', "undefined"),
                os.environ.get('VPN_TYPE', "undefined"),
                os.environ.get('GLUETUN_IP', "undefined")
            ]))
        level = 0
        hostlist_file = HOSTLIST_FILE
        while(True):
            output_file = TMP_DIR / f"result_{query_type}_{level}.txt"
            run_massdns(hostlist_file, UNBOUND_FILE, output_file, query_type)
            append_file(output_file, OUTPUT_DIR / f"all_{query_type}.txt")
            
            tmp_file = TMP_DIR / f"cname_{query_type}_{level}"
            hostlist_file = grep_cname_results(output_file, tmp_file)
            print("hostlist file:")
            print(hostlist_file)
            if not hostlist_file:
                break
            level+=1
        # extract ips from all_A.txt
        extract_ips(OUTPUT_DIR / f"all_{query_type}.txt", OUTPUT_DIR / f"ips_{query_type}.txt", query_type)
