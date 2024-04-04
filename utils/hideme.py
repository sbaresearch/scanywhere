#!/usr/bin/env python3

#https://api.hide.me/v1/login # with user and pass returns token that can be used as x-token header

PATH_HIDEME_SERVER_JSON = 'hideme_servers.json'

import json
import requests
from pathlib import Path

def update_hideme_servers(json_path = PATH_HIDEME_SERVER_JSON, url = 'https://api.hide.me/v1/network/paid/en'):
    try:
        data = requests.get(url).json()
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
    except:
        print("error updating hideme server json")
        pass

def get_hideme_servers(json_path = PATH_HIDEME_SERVER_JSON):
    # premium users:
    #https://api.hide.me/v1/network/paid/en
    #https://api.hide.me/v1/network/streaming/en
    # additionall for non premium users:
    #https://api.hide.me/v1/network/free/en
    #https://api.hide.me/v1/network/streaming-free/en
    #r = requests.get("https://api.hide.me/v1/network/paid/en")
    if not Path(json_path).is_file():
        print("hidme servers not found --> download from web")
        update_hideme_servers()    
    servers = {}
    with open(json_path) as file:
        server_json = json.loads(file.read())
    for server in server_json:
        #id = server.get('id')
        #coutry_code = server.get('geo', {}).get('countryCode', server.get('flag', '').upper())
        host = server.get('hostname')
        country = server.get('displayName')
        servers[country] = servers.get(country,[]) + [host]
    return dict(sorted(servers.items()))




if __name__ == '__main__':
    servers = get_hideme_servers()
    print(servers)