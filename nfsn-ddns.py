import requests
import argparse
import os
from ipaddress import IPv4Address, IPv6Address
from typing import Union, NewType
import random
import string

IPAddress = NewType("IPAddress", Union[IPv4Address, IPv6Address])


os.getenv('IP_PROVIDER', "http://ipinfo.io/ip")
os.getenv('IPV6_PROVIDER', "http://v6.ipinfo.io/ip")
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



if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='automate the updating of domain records to create Dynamic DNS for domains registered with NearlyFreeSpeech.net')
	# parser.add_argument('integers', metavar='N', type=int, nargs='+',
	# 					help='an integer for the accumulator')
	# parser.add_argument('--sum', dest='accumulate', action='store_const',
	# 					const=sum, default=max,
	# 					help='sum the integers (default: find the max)')

	args = parser.parse_args()
	print(args.accumulate(args.integers))