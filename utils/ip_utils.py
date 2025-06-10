import time
import socket
import requests
import requests.packages.urllib3.util.connection as urllib3_cn

PREFERED_ADDR = socket.AF_UNSPEC

def get_default_source_address(af_inet, prot=socket.SOCK_DGRAM, timeout=5):
    if af_inet == socket.AF_INET:
        return [(s. settimeout(timeout), s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, prot)]][0][2]
    elif af_inet == socket.AF_INET6:
        return [(s. settimeout(timeout), s.connect(('2001:4860:4860::8888', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET6, prot)]][0][2]
    return None

# check if the host has a (private) ipv6 addr
def is_ipv6_supported():
    try:
        return get_default_source_address(socket.AF_INET6, socket.SOCK_DGRAM) and get_default_source_address(socket.AF_INET6, socket.SOCK_STREAM) #sometimes DGRAM gets an (internal) address although we cannot access public ipv6 addrs...
    except:
        return False

def allowed_gai_family():
    ret_family = allowed_gai_family_orig()
    if ret_family in [socket.AF_UNSPEC, PREFERED_ADDR]:
        ret_family = PREFERED_ADDR
    return ret_family

allowed_gai_family_orig = urllib3_cn.allowed_gai_family
urllib3_cn.allowed_gai_family = allowed_gai_family

def get_ip_info(url="https://wtfismyip.com/json", sleeptime=2, ip_field="YourFuckingIPAddress", country_field="YourFuckingCountryCode", maxwait=60*10, proxies=None):
    time_start = time.time()
    response = None
    while not response:
        try:
            #print(f"requsting {url} ...")
            r = requests.get(url, timeout=30, proxies=proxies)
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