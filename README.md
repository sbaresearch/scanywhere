# scanywhere
Internet scanning anywhere and everywhere.

Globally deploy and distribute your Internet measurements, scans and experiments leveraging cloud infrastructure and consumer-grade VPN subscriptions.

### Features
* Providing built-in support for many popoular VPN services: e.g., nordvpn, mullvad, surfshark, protonvpn, public internet access, hidemyass, cyberghost, ivpn, hide.me, cloudflare warp
* Providing IPv6 support whenever it is available by the VPN service (e.g., Mullvad)
* Allowing to add an ephemeral Cloudflare Warp hop after the original VPN connection (helping to provide IPv6 connectivity in all countries supported by the original VPN service)
* Out-of-the-box solution for running epehemeral wireguard VPNs across all available regions on AWS EC2
  * Implementing a [deadman_switch](/utils/deadman_switch.sh) that automatically shuts down your started instances after disconnection of the corresponding VPN client (to save you from excessive AWS fees)

### Requirements
* Docker
* Python

## Usage
1. Provide credentials to your subscriptions in the `credentials.json` config file (placed in the root directory). Not used services can be deleted or left empty.

    Example `credentials.json` file (empty):
    ```
    {
        "NORD_OPENVPN_USER": "",
        "NORD_OPENVPN_PASSWORD": "",
        "NORD_WIREGUARD_PRIVATE_KEY": "",

        "MULLVAD_OPENVPN_USER": "",
        "MULLVAD_WIREGUARD_PRIVATE_KEY": "",
        "MULLVAD_WIREGUARD_ADDRESSES": "",

        "SURFSHARK_OPENVPN_USER": "",
        "SURFSHARK_OPENVPN_PASSWORD": "",
        "SURFSHARK_WIREGUARD_PRIVATE_KEY": "",
        "SURFSHARK_WIREGUARD_ADDRESSES": "",

        "PROTON_OPENVPN_USER": "",
        "PROTON_OPENVPN_PASSWORD": "",

        "PIA_OPENVPN_USER": "",
        "PIA_OPENVPN_PASSWORD": "",

        "HMA_OPENVPN_USER": "",
        "HMA_OPENVPN_PASSWORD": "",

        "CYBERGHOST_OPENVPN_USER" : "",
        "CYBERGHOST_OPENVPN_PASSWORD" : "",
        "CYBERGHOST_OPENVPN_KEY" : "",
        "CYBERGHOST_OPENVPN_CERT" : "",

        "IVPN_OPENVPN_USER" : "",
        "IVPN_WIREGUARD_PRIVATE_KEY": "",
        "IVPN_WIREGUARD_ADDRESSES": "",

        "HIDEME_OPENVPN_USER": "",
        "HIDEME_OPENVPN_PASSWORD": "",

        "EC2_ID": "",
        "EC2_KEY": ""
    }
    ```
2. Paste your SSH key into the `ssh_key.pub` file (placed in the root directory). This is only required if you want to use EC2 instances as VPN servers. The given SSH key is used to provide debugging access to the ephemeral EC2 instances.

    Example `ssh_key.pub` file:
    ```
    ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDDDRfcyC7mH3FMZ5IgdoMFI5g4aOl5rroAs0e+jJMYl2i+mtSpaZ7wkjo7uDgDARKdyDGshqq+yhUdZuzp/MX8av5XW4bZr8EKOULqMNo5jw2tSwtnMU0NNiCsPw8hT6ynnBJqJ9+9bfZuWK65h3oG9XonR+Bqh4hRVSls3jPk+/YUNicN98o02cMzerlfyGgssWvsG3wdk/gTWingzZTOciIHaG7bGq0Gz1Hh+LrSFbF2f4Z3zIg4D3C+8zpkAYjTbTI/L3KNB4vYJhgEEyTWb5lVZp34/G8+Z5Sn/HBkgd6JA0HkaivZKlelqQa6P5vkGvMi8LLi+tWzg+gwHK01
    ```

3. Install the requirements from the [requirements.txt](requirements.txt) file.

4. Run example measurement (IPv4/IPv6 connectivity check):

    `./scanywhere.py --vpn_service surfshark_open --target_image check-ip-connectivity`

5. Scanywhere will iteratively execute the docker image for the test `check-ip-connectivity` from different countries using the selected VPN service.
    > Note that the program will iteratively run the measurement over different VPN endpoints in an inifite loop. It can be terminated via Ctrl + C.

6. Check the `docker/check-ip-connectivity/results` folder to collect the results of the measurement.

### Arguments
* `--vpn_service`: the VPN service that will be used as a proxy for the measurement
* `--server_selection`: can be set to `random` (i.e., the VPN server will be chosen randomly from all available servers) or `iterative` (i.e., the script will try to iterate over the available VPN servers by country).
* `--disable_normalization`: scanywhere will try to maximize country-grade diversity and therefore group (normalize) VPN servers of the same country when iterating/selecting a particular VPN server for a measurement; this is done to not overrepresent popular countries (like US or Germany) in the measurements -- to just distribute your measurements over all IP addresses without considering their country this feature can be disabled).
* `--warp_mode`: adds an additional cloudflare container that is chained after the original VPN service

## Implemented Experiments
* IPv4/IPv6 Connectivity Check: [check-ip-connectivity](/docker/check-ip-connectivity)
* VoWiFi Geoblocking Study:
  * Mass GeoDNS Resolution: [vowifi-geoblocking-resolve-domains](/docker/vowifi-geoblocking-resolve-domains)
  * Discover Geoblocking at ePDG servers: [vowifi-geoblocking-scan-epdgs](/docker/vowifi-geoblocking-scan-epdgs)

## Customization
New experiments can be added by adding a new folder containing a dockerfile to the [docker](/docker) folder.
The current sourcecode automatically creates container volumes for the subfolders `resources` and `results`.

### Update gluetun server lists
`docker run --rm -v $(pwd)/docker/gluetun:/gluetun qmcgaw/gluetun update -enduser -providers "mullvad,nordvpn,private internet access,protonvpn,surfshark,hidemyass,cyberghost,ivpn"`

## Disclaimer and Ethical Considerations
This tool is currently in development. Although it has proven to be useful, it's not yet prepared for production and should be utilized cautiously, acknowledging any associated risks.
Likewise, we recommend to only use it for lightweight measurements -- i.e., experiments that mimic the normal behaviour of Internet users -- since excessive or invasive scaninning possibly violates the ToS of your VPN subscriptions.

## Acknowledgments
scanywhere was developed at [SBA Research](https://www.sba-research.org/) and [University of Vienna](https://sec.cs.univie.ac.at/) by [Gabriel K. Gegenhuber](https://www.sba-research.org/team/gabriel-k-gegenhuber/).

### Related Repositories
* [gluetun](https://github.com/qdm12/gluetun): used to route measurements over VPN subscriptions
* [wgcf](https://github.com/ViRb3/wgcf): used to generate ephemeral warp profiles
* [boto3](https://github.com/boto/boto3): used to automatically deploy/manage ec2 instances

### Related Measurement Paper (VoWiFi Geoblocking)
* Paper (MobiSys 2024): [Why E.T. Can't Phone Home: A Global View on IP-based Geoblocking at VoWiFi](/vowifi-mobisys24/MobiSys2024_Why_ET_Cant_Phone_Home.pdf)
* Measurement Artifacts:
  * discovered ePDG domains, IPs (by August 2023): check out the [epdgs directory](/vowifi-mobisys24/epdgs)
  * raw DNS discovery result files (8,555 domain discovery + 47,902 IP discovery rounds): check out the [dataset](https://phaidra.univie.ac.at/detail/o:2060209)
  * raw IKE probing result files (55,766 scan rounds): check out the [dataset](https://phaidra.univie.ac.at/detail/o:2060208)
  * intermediary evaluation files: check out the [evaluation directory](/vowifi-mobisys24/evaluation)
  * sqlite database (processed ePDG scan results): check out the [dataset](https://phaidra.univie.ac.at/detail/o:2059211)

If you use the code or data in your research or work, please cite the following paper:
```
@inproceedings{gegenhuber2024geoblocking,
  title={Why E.T. Can't Phone Home: A Global View on IP-based Geoblocking at VoWiFi},
  author={Gegenhuber, Gabriel K. and Frenzel, Philipp É. and Weippl, Edgar},
  booktitle={Proceedings of the 22nd Annual International Conference on Mobile Systems, Applications, and Services (MobiSys 2024)},
  year={2024},
  organization={ACM}
}
```

## License
scanywhere is licensed under GPLv3.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)