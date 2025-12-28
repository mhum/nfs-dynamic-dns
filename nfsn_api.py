"""
Shared NFSN API utilities for interacting with NearlyFreeSpeech.NET API.

This module provides common functions for authentication, HTTP requests,
and response validation when working with the NFSN RESTful API.
"""

import hashlib
import random
import requests
import string
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict

# Load environment variables from .env file
load_dotenv()

# NFSN API base domain
NFSN_API_DOMAIN = "https://api.nearlyfreespeech.net"


def randomRangeString(length: int) -> str:
    """
    Generate a random alphanumeric string of specified length.

    Args:
        length: Number of characters in the random string

    Returns:
        Random string containing uppercase, lowercase, and digit characters
    """
    character_options = string.ascii_uppercase + string.ascii_lowercase + string.digits
    random_values = [random.choice(character_options) for _ in range(length)]
    return ''.join(random_values)


def output(msg, type_msg=None, timestamp=None):
    """
    Print a formatted log message with timestamp.

    Args:
        msg: The message to output
        type_msg: Optional message type prefix (e.g., "ERROR")
        timestamp: Optional timestamp string (defaults to current time)
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")
    type_str = f"{type_msg}: " if type_msg is not None else ""
    print(f"{timestamp}: {type_str}{msg}")


def validateNFSNResponse(response):
    """
    Validate and print errors from NFSN API responses.

    Args:
        response: The response data from NFSN API
    """
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


def createNFSNAuthHeader(nfsn_username, nfsn_apikey, url_path, body) -> Dict[str, str]:
    """
    Create authentication header for NFSN API requests.

    Implements the NFSN API authentication scheme as documented at:
    https://members.nearlyfreespeech.net/wiki/API/Introduction

    Args:
        nfsn_username: NFSN account username
        nfsn_apikey: NFSN API key
        url_path: API endpoint path (e.g., "/dns/example.com/listRRs")
        body: URL-encoded request body (or empty string/None)

    Returns:
        Dictionary containing X-NFSN-Authentication header
    """
    salt = randomRangeString(16)
    timestamp = int(datetime.now(timezone.utc).timestamp())
    uts = f"{nfsn_username};{timestamp};{salt}"
    # "If there is no request body, the SHA1 hash of the empty string must be used."
    body = body or ""
    body_hash = hashlib.sha1(bytes(body, 'utf-8')).hexdigest()

    msg = f"{uts};{nfsn_apikey};{url_path};{body_hash}"

    full_hash = hashlib.sha1(bytes(msg, 'utf-8')).hexdigest()

    return {"X-NFSN-Authentication": f"{uts};{full_hash}"}


def makeNFSNHTTPRequest(path, body, nfsn_username, nfsn_apikey):
    """
    Make an authenticated POST request to the NFSN API.

    Args:
        path: API endpoint path (e.g., "/dns/example.com/addRR")
        body: URL-encoded request body (or None)
        nfsn_username: NFSN account username
        nfsn_apikey: NFSN API key

    Returns:
        Parsed JSON response data, or empty string if no response body
    """
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


def fetchDNSRecordData(name, domain, record_type, nfsn_username, nfsn_apikey):
    """
    Fetch DNS record data for a specific name and type.

    Args:
        name: Subdomain/record name (empty string for bare domain)
        domain: The domain to query
        record_type: DNS record type (e.g., "A", "AAAA", "TXT")
        nfsn_username: NFSN account username
        nfsn_apikey: NFSN API key

    Returns:
        The data field from the first matching DNS record, or None if not found
    """
    from urllib.parse import urlencode

    path = f"/dns/{domain}/listRRs"
    body = urlencode({
        "name": name or "",
        "type": record_type
    })

    response_data = makeNFSNHTTPRequest(path, body, nfsn_username, nfsn_apikey)

    if len(response_data) == 0:
        return None

    return response_data[0].get("data")


def addDNSRecord(domain, name, record_type, data, ttl, nfsn_username, nfsn_apikey):
    """
    Add a new DNS record.

    Args:
        domain: The domain to add the record to
        name: Subdomain/record name (empty string for bare domain)
        record_type: DNS record type (e.g., "A", "AAAA", "TXT")
        data: The record data (e.g., IP address, TXT value)
        ttl: Time to live in seconds
        nfsn_username: NFSN account username
        nfsn_apikey: NFSN API key
    """
    from urllib.parse import urlencode

    path = f"/dns/{domain}/addRR"
    body = urlencode({
        "name": name or "",
        "type": record_type,
        "data": data,
        "ttl": ttl
    })

    makeNFSNHTTPRequest(path, body, nfsn_username, nfsn_apikey)


def replaceDNSRecord(domain, name, record_type, data, ttl, nfsn_username, nfsn_apikey):
    """
    Replace an existing DNS record.

    Args:
        domain: The domain containing the record
        name: Subdomain/record name (empty string for bare domain)
        record_type: DNS record type (e.g., "A", "AAAA", "TXT")
        data: The new record data (e.g., IP address, TXT value)
        ttl: Time to live in seconds
        nfsn_username: NFSN account username
        nfsn_apikey: NFSN API key
    """
    from urllib.parse import urlencode

    path = f"/dns/{domain}/replaceRR"
    body = urlencode({
        "name": name or "",
        "type": record_type,
        "data": data,
        "ttl": ttl
    })

    makeNFSNHTTPRequest(path, body, nfsn_username, nfsn_apikey)


def removeDNSRecord(domain, name, record_type, data, nfsn_username, nfsn_apikey):
    """
    Remove a DNS record.

    Args:
        domain: The domain containing the record
        name: Subdomain/record name (empty string for bare domain)
        record_type: DNS record type (e.g., "A", "AAAA", "TXT")
        data: The record data to remove (must match exactly)
        nfsn_username: NFSN account username
        nfsn_apikey: NFSN API key
    """
    from urllib.parse import urlencode

    path = f"/dns/{domain}/removeRR"
    body = urlencode({
        "name": name or "",
        "type": record_type,
        "data": data
    })

    makeNFSNHTTPRequest(path, body, nfsn_username, nfsn_apikey)
