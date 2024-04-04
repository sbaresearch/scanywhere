#!/bin/bash

/unbound.sh &
/vowifi-geoblocking-resolve-domains/resolve_domains.py
#bash