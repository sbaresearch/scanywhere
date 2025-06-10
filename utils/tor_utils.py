#!/usr/bin/python3 

import time
import json
import random
import logging
import argparse
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

DETAILS_ULR = "https://onionoo.torproject.org/details"
DETAILS_FILENAME = "resources/relay_details.json"
DETAILS_MAX_AGE = timedelta(days=1)

TORRC_PATH = "/etc/tor/torrc"

def is_file_older_than(filename, delta): 
    details_file = Path(filename)
    if not details_file.is_file():
        return True
    cutoff = datetime.now(timezone.utc) - delta
    mtime = datetime.fromtimestamp(details_file.lstat().st_mtime, timezone.utc)
    if mtime < cutoff:
        return True
    return False

def download_relay_details(filename):
    if is_file_older_than(filename, DETAILS_MAX_AGE):
        logging.info(f"Downloading relay details from {DETAILS_ULR}...")
        r = requests.get(DETAILS_ULR)
        with open(filename, 'wb') as f:
            f.write(r.content)
    else:
        logging.info(f"Using cached relay details...")

def load_exit_nodes(filename):
    with open(filename, 'r') as file:
        logging.info(f"Processing relay details from {filename}...")
        details = json.load(file)
        max_time = max(datetime.strptime(r["last_seen"], "%Y-%m-%d %H:%M:%S") for r in details["relays"])
        relays = [r for r in details["relays"] if datetime.strptime(r["last_seen"], "%Y-%m-%d %H:%M:%S") >= max_time]
        relays_exit = [r for r in relays if r.get('exit_probability', 0) > 0]
        return relays_exit
    
def get_mapping(exit_relays):
    logging.info(f"Get mapping...")
    relays_per_country_code = dict()
    relays_per_country_name = dict()
    for r in exit_relays:
        relays_per_country_code.setdefault(r["country"], []).append(r['fingerprint'])
        relays_per_country_name.setdefault(r["country_name"], []).append(r['fingerprint'])
    return relays_per_country_code, relays_per_country_name
        
def select_exit_relay_fingerprint(target_country, relays_per_country_code, relays_per_country_name):
    if not target_country:
        logging.info(f"No target country set, selecting random country instead")
        target_country = random.choice(list(relays_per_country_code.keys()))
    fingerprints = relays_per_country_code.get(target_country, []) or relays_per_country_name.get(target_country, [])
    fingerprint = random.choice(fingerprints)
    logging.info(f"Selected node relay {fingerprint} in {target_country}")
    return fingerprint

def write_exit_to_torrc(exit_relay):
    logging.info(f"Writing exit relay {exit_relay} to {TORRC_PATH} config file")
    with open(TORRC_PATH, 'a') as file:
        file.write(f'\nExitNodes {exit_relay}\n')

def get_available_tor_countries(path_cache='/tmp/gluetor/'):
    path_cache = Path(path_cache)
    # ensure path exists:
    path_cache.mkdir(parents=True, exist_ok=True)
    download_relay_details(path_cache)
    exit_relays = load_exit_nodes(path_cache)
    relays_per_country_code, relays_per_country_name = get_mapping(exit_relays)
    return relays_per_country_code.keys()

 
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--write_torrc', action='store_true')
    parser.add_argument('--exit_country')
    args = parser.parse_args()
    
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    while(args.write_torrc):
        try:
            download_relay_details(DETAILS_FILENAME)
            exit_relays = load_exit_nodes(DETAILS_FILENAME)
            relays_per_country_code, relays_per_country_name = get_mapping(exit_relays)
            fingerprint = select_exit_relay_fingerprint(args.exit_country, relays_per_country_code, relays_per_country_name)
            write_exit_to_torrc(fingerprint)
            break
        except:
            logging.error("Error retrieving/processing tor relay details...")
            time.sleep(60)


