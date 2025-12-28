import argparse
import os
import requests
from ipaddress import IPv4Address, IPv6Address, ip_address
from pathlib import Path
from typing import Union, NewType

from nfsn_api import makeNFSNHTTPRequest, output, fetchDNSRecordData, addDNSRecord, replaceDNSRecord

IPAddress = NewType("IPAddress", Union[IPv4Address, IPv6Address])

IPV4_PROVIDER_URL = os.getenv('IP_PROVIDER', "http://ipinfo.io/ip")
IPV6_PROVIDER_URL = os.getenv('IPV6_PROVIDER', "http://v6.ipinfo.io/ip")

def doIPsMatch(ip1:IPAddress, ip2:IPAddress) -> bool:
    return ip1 == ip2

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
    record_type = "A" if not v6 else "AAAA"
    data = fetchDNSRecordData(subdomain or "", domain, record_type, nfsn_username, nfsn_apikey)

    if data is None:
        output("No IP address is currently set.")

    return data

def replaceDomain(domain, subdomain, current_ip, nfsn_username, nfsn_apikey, create=False, ttl=3600, v6=False):
    subdomain = subdomain or ""
    record_type = "A" if not v6 else "AAAA"

    if subdomain == "":
        output(f"Setting {record_type} record on {domain} to {current_ip}...")
    else:
        output(f"Setting {record_type} record on {subdomain}.{domain} to {current_ip}...")

    if create:
        addDNSRecord(domain, subdomain, record_type, current_ip, ttl, nfsn_username, nfsn_apikey)
    else:
        replaceDNSRecord(domain, subdomain, record_type, current_ip, ttl, nfsn_username, nfsn_apikey)

def getAllDNSRecords(domain, nfsn_username, nfsn_apikey):
    action = "listRRs"

    path = f"/dns/{domain}/{action}"

    response_data = makeNFSNHTTPRequest(path, None, nfsn_username, nfsn_apikey)

    return response_data

def NFSNDnsToZoneFile(dnsRecords):

    def sortKey(record):
        host = record.get("name")
        return ("@" if host == "" else host) \
            + record.get("data")

    dnsRecords = sorted(dnsRecords, key=sortKey )

    outputList = []
    for record in dnsRecords:
        host = record.get("name")
        host = "@" if host == "" else host
        record_type = record.get("type")
        data = record.get("data")
        if record_type == "TXT":
            data = f'"{data}"'
        elif record_type == "MX":
            data = f'{record.get("aux")} {data}'
        outputList.append(
            '\t'.join([
                host,
                str(record.get("ttl")),
                "IN",
                record_type,
                data
            ])
        )
    outputList.append("")
    return outputList

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
    parser.add_argument('--export-to', help='the filename to export the zone file to')
    args = parser.parse_args()

    nfsn_username = os.getenv('USERNAME')
    nfsn_apikey = os.getenv('API_KEY')
    nfsn_domain = os.getenv('DOMAIN')
    nfsn_subdomain = os.getenv('SUBDOMAIN')

    ensure_present(nfsn_username, "USERNAME")
    ensure_present(nfsn_apikey, "API_KEY")
    ensure_present(nfsn_domain, "DOMAIN")

    if args.export_to:

        dns = getAllDNSRecords(nfsn_domain, nfsn_username, nfsn_apikey)

        zonedata = NFSNDnsToZoneFile(dns)

        Path(args.export_to).write_text('\n'.join(zonedata), encoding='utf-8')
    else:
        use_dig_command = os.getenv('IP_USE_DIG', args.useDig)
        v6_enabled = os.getenv('ENABLE_IPV6', args.ipv6)

        check_ips(nfsn_domain, nfsn_subdomain, nfsn_username, nfsn_apikey, v6=v6_enabled, dig=use_dig_command, create_if_not_exists=False)
