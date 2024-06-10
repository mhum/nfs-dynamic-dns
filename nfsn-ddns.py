from urllib.parse import urlencode
import requests
import os
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Union, NewType
import random
import string
from datetime import datetime, timezone
import hashlib

IPAddress = NewType("IPAddress", Union[IPv4Address, IPv6Address])


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

def fetchCurrentIP():
    response = requests.get(IPV4_PROVIDER_URL)
    response.raise_for_status()
    return response.text.strip()


def fetchDomainIP(domain, subdomain, nfsn_username, nfsn_apikey):
    subdomain = subdomain or ""
    path = f"/dns/{domain}/listRRs"
    body = {
        "name": subdomain,
        "type": "A"
    }
    body = urlencode(body)

    response_data = makeNFSNHTTPRequest(path, body, nfsn_username, nfsn_apikey)

    data = list(filter(lambda r: r['name'] == subdomain, response_data))

    if len(data) == 0:
        output("No IP address is currently set.")
        return 
    
    return data[0].get("data")


def replaceDomain(domain, subdomain, current_ip, nfsn_username, nfsn_apikey, create=False, ttl=3600):

    action = "replaceRR" if not create else "addRR"

    path = f"/dns/{domain}/{action}"
    subdomain = subdomain or ""
    body = {
        "name": subdomain,
        "type": "A",
        "data": current_ip,
        "ttl": ttl
    }
    body = urlencode(body)

    if subdomain == "":
        output(f"Setting {domain} to {current_ip}...")
    else:
        output(f"Setting {subdomain}.{domain} to {current_ip}...")

    makeNFSNHTTPRequest(path, body, nfsn_username, nfsn_apikey)
    


def createNFSNAuthHeader(nfsn_username, nfsn_apikey, url_path, body) -> dict[str,str]:
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



def updateIPs(domain, subdomain, domain_ip, current_ip, nfsn_username, nfsn_apikey):
    # When there's no existing record for a domain name, the
    # listRRs API query returns the domain name of the name server.
    if domain_ip is not None and domain_ip.startswith("nearlyfreespeech.net"):
        output("The domain IP doesn't appear to be set yet.")
    else:
        output(f"Current IP: {current_ip} doesn't match Domain IP: {domain_ip or 'UNSET'}")

    replaceDomain(domain, subdomain, current_ip, nfsn_username, nfsn_apikey, create=domain_ip is None)
    # Check to see if the update was successful

    new_domain_ip = fetchDomainIP(domain, subdomain, nfsn_username, nfsn_apikey)

    if new_domain_ip is not None and doIPsMatch(ip_address(new_domain_ip), ip_address(current_ip)):
        output(f"IPs match now! Current IP: {current_ip} Domain IP: {domain_ip}")
    else:
        output(f"They still don't match. Current IP: {current_ip} Domain IP: {domain_ip}")


def ensure_present(value, name):
    if value is None:
        raise ValueError(f"Please ensure {name} is set to a value before running this script")



if __name__ == "__main__":
    nfsn_username = os.getenv('USERNAME')
    nfsn_apikey = os.getenv('API_KEY')
    nfsn_domain = os.getenv('DOMAIN')
    nfsn_subdomain = os.getenv('SUBDOMAIN')
    
    ensure_present(nfsn_username, "USERNAME")
    ensure_present(nfsn_apikey, "API_KEY")
    ensure_present(nfsn_domain, "DOMAIN")


    domain_ip = fetchDomainIP(nfsn_domain, nfsn_subdomain, nfsn_username, nfsn_apikey)
    current_ip = fetchCurrentIP()
    
    if domain_ip is not None and doIPsMatch(ip_address(domain_ip), ip_address(current_ip)):
        output(f"IPs still match!  Current IP: {current_ip} Domain IP: {domain_ip}")
    else:
        updateIPs(nfsn_domain, nfsn_subdomain, domain_ip, current_ip, nfsn_username, nfsn_apikey)
