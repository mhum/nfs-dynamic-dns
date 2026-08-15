import argparse
import os
import sys
import requests
from ipaddress import IPv4Address, IPv6Address, ip_address
from pathlib import Path
from typing import Union, NewType

from nfsn_api import makeNFSNHTTPRequest, output, fetchDNSRecordData, addDNSRecord, replaceDNSRecord

IPAddress = NewType("IPAddress", Union[IPv4Address, IPv6Address])

IPV4_PROVIDER_URL = os.getenv('IP_PROVIDER', "http://ipinfo.io/ip")
IPV6_PROVIDER_URL = os.getenv('IPV6_PROVIDER', "http://v6.ipinfo.io/ip")

# Values that turn a flag off when supplied through the environment. Anything
# else counts as on, so `ENABLE_IPV6=1` and `ENABLE_IPV6=yes` both work.
FALSY_ENV_VALUES = frozenset(["", "0", "false", "no", "off"])

def env_flag(name, default=False) -> bool:
    value = os.getenv(name)
    if value is None:
        return bool(default)
    return value.strip().lower() not in FALSY_ENV_VALUES

def doIPsMatch(ip1, ip2) -> bool:
    try:
        return ip_address(ip1) == ip_address(ip2)
    except ValueError:
        return False

def isDomainIPUnset(domain_ip) -> bool:
    # With no record in place, listRRs answers with the name server's domain
    # rather than an address, so anything unparseable means "not set yet".
    if domain_ip is None:
        return True
    try:
        ip_address(domain_ip)
    except ValueError:
        return True
    return False

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
    unset = isDomainIPUnset(domain_ip)

    if unset:
        output("The domain IP doesn't appear to be set yet.")
    else:
        output(f"Current IP: {current_ip} doesn't match Domain IP: {domain_ip}")

    replaceDomain(domain, subdomain, current_ip, nfsn_username, nfsn_apikey, create=unset and create_if_not_exists, v6=v6)
    # Check to see if the update was successful

    new_domain_ip = fetchDomainIP(domain, subdomain, nfsn_username, nfsn_apikey, v6=v6)

    if doIPsMatch(new_domain_ip, current_ip):
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

    if doIPsMatch(domain_ip, current_ip):
        output(f"IPs still match!  Current IP: {current_ip} Domain IP: {domain_ip}")
        return

    updateIPs(nfsn_domain, nfsn_subdomain, domain_ip, current_ip, nfsn_username, nfsn_apikey, v6=v6, create_if_not_exists=create_if_not_exists)

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='automate the updating of domain records to create Dynamic DNS for domains registered with NearlyFreeSpeech.net')
    parser.add_argument('--ipv6', '-6', action='store_true', help='also check and update the AAAA (IPv6) record')
    parser.add_argument('--no-ipv4', action='store_true', help='skip the A (IPv4) record; combine with --ipv6 for an IPv6-only run')
    parser.add_argument('--useDig', '-d', action='store_true', help='use the dig command to query dns')
    parser.add_argument('--export-to', help='the filename to export the zone file to')
    args = parser.parse_args(argv)

    # Misconfiguration is a user error, not a crash: report it in one line.
    try:
        return run(args)
    except ValueError as error:
        output(error, type_msg="ERROR")
        return 1

def run(args) -> int:
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
        return 0

    use_dig_command = env_flag('IP_USE_DIG', args.useDig)
    v4_enabled = env_flag('ENABLE_IPV4', not args.no_ipv4)
    v6_enabled = env_flag('ENABLE_IPV6', args.ipv6)

    if not v4_enabled and not v6_enabled:
        raise ValueError("Nothing to update: enable at least one of ENABLE_IPV4 or ENABLE_IPV6")

    # IPv4 goes first so a host without working IPv6 still gets its A record
    # updated before the AAAA attempt fails.
    families = [v6 for v6, enabled in ((False, v4_enabled), (True, v6_enabled)) if enabled]

    failed = False
    for v6 in families:
        try:
            check_ips(nfsn_domain, nfsn_subdomain, nfsn_username, nfsn_apikey, v6=v6, dig=use_dig_command, create_if_not_exists=True)
        except Exception as error:
            record_type = "AAAA" if v6 else "A"
            output(f"Could not update the {record_type} record: {error}", type_msg="ERROR")
            failed = True

    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
