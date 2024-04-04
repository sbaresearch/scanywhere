# scanywhere
Globally deploy your Internet measurements, scans and experiments leveraging cloud infrastructure and consumer-grade VPN subscriptions

## Usage
1. Provide credentials to your subscriptions in the `credentials.json` config file (placed in the root directory). Not used services can be deleted or left empty.

    Example `credentials.json` file:
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
2. Paste your SSH key into the `ssh_key.pub` file. This is only required if you want to use EC2 instances as VPN servers. The provided SSH key is used to provide debugging access to the ephemeral EC2 instances.

    Example `ssh_key.pub` file:
    ```
    ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDDDRfcyC7mH3FMZ5IgdoMFI5g4aOl5rroAs0e+jJMYl2i+mtSpaZ7wkjo7uDgDARKdyDGshqq+yhUdZuzp/MX8av5XW4bZr8EKOULqMNo5jw2tSwtnMU0NNiCsPw8hT6ynnBJqJ9+9bfZuWK65h3oG9XonR+Bqh4hRVSls3jPk+/YUNicN98o02cMzerlfyGgssWvsG3wdk/gTWingzZTOciIHaG7bGq0Gz1Hh+LrSFbF2f4Z3zIg4D3C+8zpkAYjTbTI/L3KNB4vYJhgEEyTWb5lVZp34/G8+Z5Sn/HBkgd6JA0HkaivZKlelqQa6P5vkGvMi8LLi+tWzg+gwHK01
    ```

3. Run example measurement (IPv4/IPv6 connectivity check):
`./scanywhere.py --vpn_type surfshark_open --target_image check-ip-connectivity`

## Implemented Experiments
- IPv4/IPv6 Connectivity Check: 
- VoWiFi Geoblocking Study: [check-ip-connectivity](/docker/check-ip-connectivity)
  - Mass GeoDNS Resolution: [vowifi-geoblocking-resolve-domains](/docker/vowifi-geoblocking-resolve-domains)
  - Discover Geoblocking at ePDG servers: [vowifi-geoblocking-scan-epdgs](/docker/vowifi-geoblocking-scan-epdgs)

### Update gluetun server lists
`docker run --rm -v $(pwd)/docker/gluetun:/gluetun qmcgaw/gluetun update -enduser -providers "mullvad,nordvpn,private internet access,protonvpn,surfshark,hidemyass,cyberghost,ivpn"`

## Related Repositories and Credits
* [gluetun](https://github.com/qdm12/gluetun): used to route measurements over VPN subscriptions
* [wgcf](https://github.com/ViRb3/wgcf): used to generate ephemeral warp profiles
* [boto3](https://github.com/boto/boto3): used to automatically deploy/manage ec2 instances