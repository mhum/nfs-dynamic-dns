#!/bin/bash

# NFSN DNS API plugin for acme.sh
# Requires: USERNAME, API_KEY, DOMAIN environment variables

dns_nfsn_add() {
  fulldomain=$1
  txtvalue=$2

  # Extract subdomain from fulldomain
  # For _acme-challenge.example.com, we want _acme-challenge
  # For _acme-challenge.*.example.com, we want _acme-challenge.*
  subdomain="${fulldomain%.$DOMAIN}"

  echo "[ACME] Adding DNS record: $subdomain = $txtvalue"
  python3 /root/nfsn-acme.py auth "$txtvalue" "$subdomain"

  # Wait for DNS propagation
  sleep 30

  return 0
}

dns_nfsn_rm() {
  fulldomain=$1
  txtvalue=$2

  # Extract subdomain from fulldomain
  subdomain="${fulldomain%.$DOMAIN}"

  echo "[ACME] Removing DNS record: $subdomain"
  python3 /root/nfsn-acme.py cleanup "$subdomain"

  return 0
}
