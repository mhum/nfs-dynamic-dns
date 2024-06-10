import requests
import argparse
import os
from ipaddress import IPv4Address, IPv6Address
from typing import Union, NewType
import random
import string
from datetime import datetime, timezone
import hashlib

IPAddress = NewType("IPAddress", Union[IPv4Address, IPv6Address])


IPV4_PROVIDER_URL = os.getenv('IP_PROVIDER', "http://ipinfo.io/ip")
IPV6_PROVIDER_URL = os.getenv('IPV6_PROVIDER', "http://v6.ipinfo.io/ip")
os.getenv('USERNAME', "http://v6.ipinfo.io/ip")
os.getenv('API_KEY', "http://v6.ipinfo.io/ip")
os.getenv('DOMAIN', "http://v6.ipinfo.io/ip")
# os.getenv('IPV6_PROVIDER', "http://v6.ipinfo.io/ip")
# os.getenv('IPV6_PROVIDER', "http://v6.ipinfo.io/ip")

NFSN_API_DOMAIN = "https://api.nearlyfreespeech.net"


def randomRangeString(length:int) -> str:
    character_options = string.ascii_uppercase + string.ascii_lowercase + string.digits
    random_values = [random.choice(character_options) for _ in range(length)]
    return ''.join(random_values)


def doIPsMatch(ip1:IPAddress, ip2:IPAddress) -> bool:
    return ip1 == ip2


def validateNFSNResponse(response):
    if response.get("error") is not None:
        timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")  
        print(f"{timestamp}: ERROR: {response.get('error')}")
        print(f"{timestamp}: ERROR: {response.get('debug')}")


def makeNFSNHTTPRequest(path, body, nfsn_username, nfsn_apikey):
    url = NFSN_API_DOMAIN + path
    headers = createNFSNAuthHeader(nfsn_username, nfsn_apikey, url, body)

    response = requests.get(url, body=body, headers=headers)
    
    data = response.body()

    validateNFSNResponse(data)

    return data


def createNFSNAuthHeader(nfsn_username, nfsn_apikey, uri, body) -> dict[str,str]:
    salt = randomRangeString(16)
    timestamp = int(datetime.now(timezone.utc).time().time())
    uts = f"{nfsn_username};{timestamp};{salt}"

    body_hash = str(hashlib.sha1(bytes(body, 'utf-8')))

    msg = f"{uts};{nfsn_apikey};{uri};{body_hash}"

    full_hash = str(hashlib.sha1(bytes(msg, 'utf-8')))

    return {"X-NFSN-Authentication": f"{uts};{full_hash}"}




if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='automate the updating of domain records to create Dynamic DNS for domains registered with NearlyFreeSpeech.net')
	# parser.add_argument('integers', metavar='N', type=int, nargs='+',
	# 					help='an integer for the accumulator')
	# parser.add_argument('--sum', dest='accumulate', action='store_const',
	# 					const=sum, default=max,
	# 					help='sum the integers (default: find the max)')

	args = parser.parse_args()
	print(args.accumulate(args.integers))
