import argparse
import hashlib
import random
import string
import os
from datetime import datetime, timezone
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Union, NewType, Dict
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

IPAddress = NewType("IPAddress", Union[IPv4Address, IPv6Address])

#load variables set in .env file
load_dotenv()

IPV4_PROVIDER_URL = os.getenv('IP_PROVIDER', "http://ipinfo.io/ip")
IPV6_PROVIDER_URL = os.getenv('IPV6_PROVIDER', "http://v6.ipinfo.io/ip")

NFSN_API_DOMAIN = "https://api.nearlyfreespeech.net"


def randomRangeString(length:int) -> str:
    character_options = string.ascii_uppercase + string.ascii_lowercase + string.digits
    random_values = [random.choice(character_options) for _ in range(length)]
    return ''.join(random_values)


def doIPsMatch(ip1:IPAddress, ip2:IPAddress) -> bool:
    return ip1 == ip2


def output(msg, type_msg=None, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")
    type_str = f"{type_msg}: " if type_msg is not None else ""
    print(f"{timestamp}: {type_str}{msg}")


def validateNFSNResponse(response):
    if response is None:
        print("none response received")
        return
    elif response == "":
        print("empty string received")
        return
    elif response == []:
        print("empty list received")
        return

    try:
        response = response[0]
    except Exception:
        pass
    if response.get("error") is not None:
        output(response.get('error'), type_msg="ERROR")
        output(response.get('debug'), type_msg="ERROR")


def makeNFSNHTTPRequest(path, body, nfsn_username, nfsn_apikey):
    url = NFSN_API_DOMAIN + path
    headers = createNFSNAuthHeader(nfsn_username, nfsn_apikey, path, body)
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    response = requests.post(url, data=body, headers=headers)
    # response.raise_for_status()
    if response.text != "":
        data = response.json()
    else:
        data = ""
    validateNFSNResponse(data)

    return data

def fetchCurrentIP(v6=False):
    response = requests.get(IPV4_PROVIDER_URL if not v6 else IPV6_PROVIDER_URL)
    response.raise_for_status()
    return response.text.strip()

def digCurrentIP(v6=False):
    #Use the system's dig command to ask a DNS server for my IP address
    #https://unix.stackexchange.com/questions/22615/how-can-i-get-my-external-ip-address-in-a-shell-script
    ip_version = "-4" if not v6 else "-6"
    command_string = "dig {} TXT +short o-o.myaddr.l.google.com @ns1.google.com".format(ip_version)
    return os.popen(command_string).read().split()[0].replace('"', '')

def fetchDomainIP(domain, subdomain, nfsn_username, nfsn_apikey, v6=False):
    subdomain = subdomain or ""
    path = f"/dns/{domain}/listRRs"
    record_type = "A" if not v6 else "AAAA"
    body = {
        "name": subdomain,
        "type": record_type
    }
    body = urlencode(body)

    response_data = makeNFSNHTTPRequest(path, body, nfsn_username, nfsn_apikey)

    if len(response_data) == 0:
        output("No IP address is currently set.")
        return

    return response_data[0].get("data")


def replaceDomain(domain, subdomain, current_ip, nfsn_username, nfsn_apikey, create=False, ttl=3600, v6=False):

    action = "replaceRR" if not create else "addRR"

    path = f"/dns/{domain}/{action}"
    subdomain = subdomain or ""
    record_type = "A" if not v6 else "AAAA"
    body = {
        "name": subdomain,
        "type": record_type,
        "data": current_ip,
        "ttl": ttl
    }
    body = urlencode(body)

    if subdomain == "":
        output(f"Setting {record_type} record on {domain} to {current_ip}...")
    else:
        output(f"Setting {record_type} record on {subdomain}.{domain} to {current_ip}...")

    makeNFSNHTTPRequest(path, body, nfsn_username, nfsn_apikey)



def createNFSNAuthHeader(nfsn_username, nfsn_apikey, url_path, body) -> Dict[str,str]:
    # See https://members.nearlyfreespeech.net/wiki/API/Introduction for how this auth process works

    salt = randomRangeString(16)
    timestamp = int(datetime.now(timezone.utc).timestamp())
    uts = f"{nfsn_username};{timestamp};{salt}"
    # "If there is no request body, the SHA1 hash of the empty string must be used."
    body = body or ""
    body_hash = hashlib.sha1(bytes(body, 'utf-8')).hexdigest()

    msg = f"{uts};{nfsn_apikey};{url_path};{body_hash}"

    full_hash = hashlib.sha1(bytes(msg, 'utf-8')).hexdigest()

    return {"X-NFSN-Authentication": f"{uts};{full_hash}"}


def getAllDNSRecords(domain, nfsn_username, nfsn_apikey):
    action = "listRRs"

    path = f"/dns/{domain}/{action}"

    response_data = makeNFSNHTTPRequest(path, None, nfsn_username, nfsn_apikey)

    return response_data

def updateIPs(domain, subdomain, domain_ip, current_ip, nfsn_username, nfsn_apikey, v6=False, create_if_not_exists=False):
    # When there's no existing record for a domain name, the
    # listRRs API query returns the domain name of the name server.
    if domain_ip is not None and domain_ip.startswith("nearlyfreespeech.net"):
        output("The domain IP doesn't appear to be set yet.")
    else:
        output(f"Current IP: {current_ip} doesn't match Domain IP: {domain_ip or 'UNSET'}")

    replaceDomain(domain, subdomain, current_ip, nfsn_username, nfsn_apikey, create=domain_ip is None and create_if_not_exists, v6=v6)
    # Check to see if the update was successful

    new_domain_ip = fetchDomainIP(domain, subdomain, nfsn_username, nfsn_apikey, v6=v6)

    if new_domain_ip is not None and doIPsMatch(ip_address(new_domain_ip), ip_address(current_ip)):
        output(f"IPs match now! Current IP: {current_ip} Domain IP: {domain_ip}")
    else:
        output(f"They still don't match. Current IP: {current_ip} Domain IP: {domain_ip}")


def ensure_present(value, name):
    if value is None:
        raise ValueError(f"Please ensure {name} is set to a value before running this script")


def check_ips(nfsn_domain, nfsn_subdomain, nfsn_username, nfsn_apikey, v6=False, dig=False, create_if_not_exists=False):

    domain_ip = fetchDomainIP(nfsn_domain, nfsn_subdomain, nfsn_username, nfsn_apikey, v6=v6)
    if dig:
        current_ip = digCurrentIP(v6=v6)
    else:
        current_ip = fetchCurrentIP(v6=v6)
    
    if domain_ip is not None and doIPsMatch(ip_address(domain_ip), ip_address(current_ip)):
        output(f"IPs still match!  Current IP: {current_ip} Domain IP: {domain_ip}")
        return

    updateIPs(nfsn_domain, nfsn_subdomain, domain_ip, current_ip, nfsn_username, nfsn_apikey, v6=v6)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='automate the updating of domain records to create Dynamic DNS for domains registered with NearlyFreeSpeech.net')
    parser.add_argument('--ipv6', '-6', action='store_true', help='also check and update the AAAA (IPv6) records')
    parser.add_argument('--useDig', '-d', action='store_true', help='use the dig command to query dns')
    args = parser.parse_args()
    
    nfsn_username = os.getenv('USERNAME')
    nfsn_apikey = os.getenv('API_KEY')
    nfsn_domain = os.getenv('DOMAIN')
    nfsn_subdomain = os.getenv('SUBDOMAIN')

    ensure_present(nfsn_username, "USERNAME")
    ensure_present(nfsn_apikey, "API_KEY")
    ensure_present(nfsn_domain, "DOMAIN")

    use_dig_command = os.getenv('IP_USE_DIG', args.useDig)
    v6_enabled = os.getenv('ENABLE_IPV6', args.ipv6)

    check_ips(nfsn_domain, nfsn_subdomain, nfsn_username, nfsn_apikey, v6=v6_enabled, dig=use_dig_command, create_if_not_exists=False)
