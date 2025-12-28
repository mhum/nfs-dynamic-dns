import os
import sys

from nfsn_api import fetchDNSRecordData, addDNSRecord, removeDNSRecord

def fetchDomainValue(name, domain, nfsn_username, nfsn_apikey):
    return fetchDNSRecordData(name, domain, "TXT", nfsn_username, nfsn_apikey)

def createTxtRecord(name, value, domain, nfsn_username, nfsn_apikey):
    addDNSRecord(domain, name, "TXT", value, 300, nfsn_username, nfsn_apikey)
    print(f"[ACME] Created TXT record {name}={value}")

def deleteTxtRecord(name, domain, nfsn_username, nfsn_apikey):
    value = fetchDomainValue(name, domain, nfsn_username, nfsn_apikey)

    if value is None:
        print(f"[ACME] No TXT record found for {name}, skipping deletion")
        return

    removeDNSRecord(domain, name, "TXT", value, nfsn_username, nfsn_apikey)
    print(f"[ACME] Deleted TXT record {name}")

if __name__ == "__main__":
    nfsn_username = os.getenv('USERNAME')
    nfsn_apikey = os.getenv('API_KEY')
    nfsn_domain = os.getenv('DOMAIN')

    if not nfsn_username or not nfsn_apikey or not nfsn_domain:
      print("Missing required environment variables (NFSN_USER, NFSN_API_KEY, DOMAIN)")
      sys.exit(1)

    if len(sys.argv) < 2:
        sys.exit(0)
    command = sys.argv[1]
    if command == "auth":
        token = sys.argv[2]
        subdomain = sys.argv[3]
        createTxtRecord(subdomain, token, nfsn_domain, nfsn_username, nfsn_apikey)
    elif command == "cleanup":
        subdomain = sys.argv[2]
        deleteTxtRecord(subdomain, nfsn_domain, nfsn_username, nfsn_apikey)
